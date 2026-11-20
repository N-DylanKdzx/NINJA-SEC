#!/bin/bash
set -eu
install -d /var/lib/ninjasec-health
printf '%s\n' 'ninjasec isolated health check' > /var/lib/ninjasec-health/index.html
cat > /etc/systemd/system/ninjasec-health.service <<'UNIT'
[Unit]
Description=NINJA-SEC isolated health endpoint
After=network.target

[Service]
ExecStart=/usr/bin/python3 -m http.server 8080 --directory /var/lib/ninjasec-health
DynamicUser=yes
NoNewPrivileges=yes
Restart=on-failure

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now ninjasec-health.service
