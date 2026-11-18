#!/bin/bash
# Persistent evidence and process recovery; does not reboot or disable kdump.
set -euo pipefail
install -d -m 755 /etc/systemd/journald.conf.d
printf '[Journal]\nStorage=persistent\nSystemMaxUse=64M\nRuntimeMaxUse=16M\nSystemKeepFree=1G\nMaxRetentionSec=14day\n' > /etc/systemd/journald.conf.d/90-ninjasec.conf
install -d -m 2755 -o root -g systemd-journal /var/log/journal
systemd-tmpfiles --create --prefix /var/log/journal
systemctl restart systemd-journald
journalctl --flush
systemctl disable --now dnf-makecache.timer
for unit in sshd ninjasec-portal ninjasec-grafana ninjasec-prometheus ninjasec-node-exporter ninjasec-mysql-metrics ninjasec-grafana-fallback ninjasec-azure-snapshot; do
  if systemctl cat "$unit.service" >/dev/null 2>&1; then
    install -d -m 755 "/etc/systemd/system/$unit.service.d"
    printf '[Unit]\nStartLimitIntervalSec=0\n[Service]\nRestart=on-failure\nRestartSec=5s\n' > "/etc/systemd/system/$unit.service.d/recovery.conf"
    systemctl enable "$unit.service"
  fi
done
# mcelog exits on these AMD virtual CPUs; do not report that unsupported daemon
# as an application failure. Kernel hardware-error logging remains enabled.
if journalctl -u mcelog -b --no-pager | grep -q 'CPU is unsupported'; then
  systemctl disable --now mcelog.service
  systemctl reset-failed mcelog.service || true
fi
systemctl daemon-reload
systemctl --failed --no-pager
free -m
