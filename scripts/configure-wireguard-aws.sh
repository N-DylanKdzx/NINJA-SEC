#!/bin/bash
set -euo pipefail
sysctl -w net.ipv4.ip_forward=1
iptables -N NINJASEC_WG 2>/dev/null || true
iptables -F NINJASEC_WG
iptables -A NINJASEC_WG -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
for app in 10.10.10.0/24 10.10.11.0/24; do
  iptables -A NINJASEC_WG -s "$app" -d 10.20.10.191/32 -p tcp --dport 3306 -j ACCEPT
done
for db in 10.10.20.0/24 10.10.21.0/24; do
  iptables -A NINJASEC_WG -s 10.20.10.191/32 -d "$db" -p tcp --dport 3306 -j ACCEPT
done
iptables -A NINJASEC_WG -j DROP
for side in -i -o; do
  iptables -C FORWARD "$side" wg0 -j NINJASEC_WG 2>/dev/null || iptables -I FORWARD 1 "$side" wg0 -j NINJASEC_WG
done
iptables -N NINJASEC_WG_HOST 2>/dev/null || true
iptables -F NINJASEC_WG_HOST
iptables -A NINJASEC_WG_HOST -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A NINJASEC_WG_HOST -s 10.255.254.2/32 -p icmp -j ACCEPT
iptables -A NINJASEC_WG_HOST -j DROP
iptables -C INPUT -i wg0 -j NINJASEC_WG_HOST 2>/dev/null || iptables -I INPUT 1 -i wg0 -j NINJASEC_WG_HOST
iptables -t mangle -C FORWARD -o wg0 -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu 2>/dev/null || iptables -t mangle -A FORWARD -o wg0 -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu
iptables-save > /etc/sysconfig/iptables
install -d /etc/systemd/system/wg-quick@wg0.service.d
printf '[Unit]\nAfter=iptables.service\n' > /etc/systemd/system/wg-quick@wg0.service.d/firewall.conf
systemctl daemon-reload
iptables -S NINJASEC_WG
