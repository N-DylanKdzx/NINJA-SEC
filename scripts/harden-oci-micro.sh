#!/bin/bash
# Small OCI utility/agent hosts: recover memory reserved for crash dumps.
# Kernel dumps are disabled; bounded persistent journals remain available.
set -euo pipefail
install -d -m 700 /var/lib/ninjasec/recovery
test -e /var/lib/ninjasec/recovery/grub.original || cp -a /etc/default/grub /var/lib/ninjasec/recovery/grub.original
systemctl disable --now kdump.service
grubby --update-kernel=ALL --remove-args='crashkernel' --args='crashkernel=0'
python3 - <<'PY'
from pathlib import Path
import re
p=Path('/etc/default/grub')
s=p.read_text()
s=re.sub(r'crashkernel=[^\s"\']+', 'crashkernel=0', s)
p.write_text(s)
PY
install -d -m 755 /etc/systemd/journald.conf.d
cat > /etc/systemd/journald.conf.d/90-ninjasec.conf <<'EOF'
[Journal]
Storage=persistent
SystemMaxUse=64M
RuntimeMaxUse=16M
SystemKeepFree=1G
MaxRetentionSec=14day
EOF
install -d -m 2755 -o root -g systemd-journal /var/log/journal
systemd-tmpfiles --create --prefix /var/log/journal
systemctl restart systemd-journald
journalctl --flush
# Package maintenance is manual on this small host, never automatic metadata
# downloads without a memory budget. This does not disable audit/security logs.
systemctl disable --now dnf-makecache.timer
install -d -m 755 /etc/systemd/system/dnf-makecache.service.d
printf '[Service]\nMemoryHigh=192M\nMemoryMax=256M\nMemorySwapMax=256M\n' > /etc/systemd/system/dnf-makecache.service.d/memory.conf
for unit in sshd ninjasec-portal ninjasec-grafana ninjasec-prometheus ninjasec-node-exporter ninjasec-mysql-metrics; do
  if systemctl cat "$unit.service" >/dev/null 2>&1; then
    install -d -m 755 "/etc/systemd/system/$unit.service.d"
    printf '[Unit]\nStartLimitIntervalSec=0\n[Service]\nRestart=on-failure\nRestartSec=5s\n' > "/etc/systemd/system/$unit.service.d/recovery.conf"
    systemctl enable "$unit.service"
  fi
done
systemctl daemon-reload
grubby --info=DEFAULT | grep '^args='
systemctl is-enabled kdump.service || true
systemctl is-enabled dnf-makecache.timer || true
journalctl --disk-usage
free -m
