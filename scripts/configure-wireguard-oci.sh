#!/bin/bash
set -euo pipefail
for policy in ninjasec-wg-to-vcn ninjasec-vcn-to-wg; do
  firewall-cmd --permanent --get-policies | tr ' ' '\n' | grep -qx "$policy" || firewall-cmd --permanent --new-policy="$policy"
  firewall-cmd --permanent --policy="$policy" --set-target=DROP
done
firewall-cmd --permanent --policy=ninjasec-wg-to-vcn --add-ingress-zone=ninjasec-wg
firewall-cmd --permanent --policy=ninjasec-wg-to-vcn --add-egress-zone=public
firewall-cmd --permanent --policy=ninjasec-vcn-to-wg --add-ingress-zone=public
firewall-cmd --permanent --policy=ninjasec-vcn-to-wg --add-egress-zone=ninjasec-wg
for app in 10.10.10.0/24 10.10.11.0/24; do
  firewall-cmd --permanent --policy=ninjasec-wg-to-vcn --add-rich-rule="rule family=\"ipv4\" source address=\"$app\" destination address=\"10.20.10.191/32\" port port=\"3306\" protocol=\"tcp\" accept"
done
for db in 10.10.20.0/24 10.10.21.0/24; do
  firewall-cmd --permanent --policy=ninjasec-vcn-to-wg --add-rich-rule="rule family=\"ipv4\" source address=\"10.20.10.191/32\" destination address=\"$db\" port port=\"3306\" protocol=\"tcp\" accept"
done
firewall-cmd --permanent --direct --add-rule ipv4 mangle FORWARD 0 -o wg0 -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu
printf 'net.ipv4.ip_forward=1\n' > /etc/sysctl.d/92-ninjasec-wireguard.conf
sysctl -p /etc/sysctl.d/92-ninjasec-wireguard.conf
firewall-cmd --reload
firewall-cmd --info-policy=ninjasec-wg-to-vcn
firewall-cmd --info-policy=ninjasec-vcn-to-wg
