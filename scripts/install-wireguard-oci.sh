#!/bin/bash
# Input RPM must be the Oracle-signed OL9 package, uploaded through Bastion.
# Extract only the required upstream tools: no DNS= option is used, so resolved
# is unnecessary. Do not bypass RPM dependency checks with --nodeps.
set -euo pipefail
rpm -K /tmp/ninjasec-wireguard-tools.rpm | grep -q 'digests signatures OK'
test "$(sha256sum /tmp/ninjasec-wireguard-tools.rpm | cut -d' ' -f1)" = 634f160c5a3f89cfb7af9538be530ed912d0be8acdb9f3ba2a7a2bc4f8697289
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
cd "$stage"
rpm2cpio /tmp/ninjasec-wireguard-tools.rpm | cpio -idm --quiet ./usr/bin/wg ./usr/bin/wg-quick ./usr/lib/systemd/system/wg-quick@.service
install -m 755 usr/bin/wg /usr/local/bin/wg
install -m 755 usr/bin/wg-quick /usr/local/bin/wg-quick
sed 's|/usr/bin/wg-quick|/usr/local/bin/wg-quick|g' usr/lib/systemd/system/wg-quick@.service > /etc/systemd/system/wg-quick@.service
install -d -m 700 /etc/wireguard
systemctl daemon-reload
modprobe wireguard
ldd /usr/local/bin/wg
/usr/local/bin/wg --version
rm /tmp/ninjasec-wireguard-tools.rpm
