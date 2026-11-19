#!/bin/bash
set -eu
systemctl disable --now wg-quick@wg0 2>/dev/null || true
systemctl disable --now dnf-makecache.timer 2>/dev/null || true
mkdir -p /etc/systemd/system/dnf-makecache.service.d
printf '[Service]\nMemoryHigh=192M\nMemoryMax=256M\nMemorySwapMax=256M\n' > /etc/systemd/system/dnf-makecache.service.d/memory.conf
systemctl daemon-reload
if systemctl is-active --quiet firewalld; then
 firewall-cmd --permanent --zone=public --add-rich-rule='rule family="ipv4" source address="10.20.10.105/32" port port="22" protocol="tcp" accept'
 firewall-cmd --reload
fi
systemctl enable --now sshd
systemctl restart sshd
