#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
# Private instances use the HTTPS-only NAT policy.
sed -i 's|http://|https://|g' /etc/apt/sources.list.d/ubuntu.sources
apt-get -o Acquire::Retries=5 update
apt-get -o Acquire::Retries=5 install -y nginx libnginx-mod-http-modsecurity modsecurity-crs python3-venv
python3 -m venv /opt/ninjasec-venv
/opt/ninjasec-venv/bin/pip install -r /opt/ninjasec-portal/requirements.txt
mkdir -p /etc/modsecurity
cp /etc/nginx/modsecurity.conf /etc/modsecurity/ninjasec.conf
cp /etc/nginx/unicode.mapping /etc/modsecurity/unicode.mapping
sed -i 's/^SecRuleEngine DetectionOnly/SecRuleEngine On/' /etc/modsecurity/ninjasec.conf
cat > /etc/nginx/ninjasec-waf.conf <<'EOF'
Include /etc/modsecurity/ninjasec.conf
Include /etc/modsecurity/crs/crs-setup.conf
Include /usr/share/modsecurity-crs/rules/*.conf
EOF
cat > /etc/nginx/sites-available/default <<'EOF'
server {
    listen 80 default_server;
    server_name _;
    server_tokens off;
    modsecurity on;
    modsecurity_rules_file /etc/nginx/ninjasec-waf.conf;
    location ~ ^/(portal\.css|portal\.js|login\.js)$ {
        root /opt/ninjasec-portal;
        add_header X-Content-Type-Options nosniff always;
    }
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
EOF
cat > /etc/systemd/system/ninjasec-portal.service <<'EOF'
[Unit]
Description=NINJA-SEC AWS portal API
After=network-online.target
Wants=network-online.target
ConditionPathExists=/etc/ninjasec-portal.env
[Service]
DynamicUser=yes
EnvironmentFile=/etc/ninjasec-portal.env
Environment=PORTAL_BIND=127.0.0.1
WorkingDirectory=/opt/ninjasec-portal
ExecStart=/opt/ninjasec-venv/bin/python /opt/ninjasec-portal/app.py
Restart=on-failure
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable nginx ninjasec-portal
nginx -t
systemctl restart nginx
# API starts only after its real DB and portal credentials are provisioned.
systemctl start ninjasec-portal
