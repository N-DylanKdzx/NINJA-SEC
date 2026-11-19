#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
# Private instances use the HTTPS-only NAT policy.
sed -i 's|http://|https://|g' /etc/apt/sources.list.d/ubuntu.sources
apt-get -o Acquire::Retries=5 update
apt-get -o Acquire::Retries=5 install -y nginx libnginx-mod-http-modsecurity modsecurity-crs python3-venv
python3 -m venv /opt/ninjasec-venv
/opt/ninjasec-venv/bin/pip install -r /opt/ninjasec-portal/requirements.txt
/opt/ninjasec-venv/bin/pip install boto3
mkdir -p /etc/modsecurity
cp /etc/nginx/modsecurity.conf /etc/modsecurity/ninjasec.conf
cp /etc/nginx/unicode.mapping /etc/modsecurity/unicode.mapping
sed -i 's/^SecRuleEngine DetectionOnly/SecRuleEngine On/' /etc/modsecurity/ninjasec.conf
cat > /etc/nginx/ninjasec-waf.conf <<'EOF'
Include /etc/modsecurity/ninjasec.conf
Include /etc/modsecurity/crs/crs-setup.conf
SecRule REQUEST_FILENAME "@rx ^/api/incidents/[1-9][0-9]{0,18}$" "id:10001,phase:1,pass,nolog,chain"
    SecRule REQUEST_METHOD "@rx ^(?:PUT|DELETE)$" "ctl:ruleRemoveById=911100"
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
StandardOutput=append:/var/log/ninjasec-portal.log
StandardError=append:/var/log/ninjasec-portal.log
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

# CloudWatch uses the EC2 instance profile, without static AWS credentials.
curl --fail --retry 5 -o /tmp/amazon-cloudwatch-agent.deb https://amazoncloudwatch-agent.s3.amazonaws.com/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
dpkg -i /tmp/amazon-cloudwatch-agent.deb
rm /tmp/amazon-cloudwatch-agent.deb
cat > /opt/aws/amazon-cloudwatch-agent/etc/ninjasec.json <<'CWAJSON'
{
  "agent": {
    "metrics_collection_interval": 60,
    "run_as_user": "root"
  },
  "metrics": {
    "namespace": "NINJA-SEC/Host",
    "append_dimensions": {
      "InstanceId": "${aws:InstanceId}"
    },
    "metrics_collected": {
      "mem": {
        "measurement": [
          "mem_used_percent"
        ]
      },
      "disk": {
        "measurement": [
          "used_percent"
        ],
        "resources": [
          "/"
        ],
        "drop_device": true
      }
    }
  },
  "logs": {
    "force_flush_interval": 5,
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/nginx/error.log",
            "log_group_name": "/ninjasec/waf/blocked",
            "log_stream_name": "{instance_id}",
            "retention_in_days": 7
          },
          {
            "file_path": "/var/log/nginx/access.log",
            "log_group_name": "/ninjasec/nginx/access",
            "log_stream_name": "{instance_id}",
            "retention_in_days": 7
          },
          {
            "file_path": "/var/log/ninjasec-portal.log",
            "log_group_name": "/ninjasec/app",
            "log_stream_name": "{instance_id}",
            "retention_in_days": 7
          }
        ]
      }
    }
  }
}
CWAJSON
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -s -c file:/opt/aws/amazon-cloudwatch-agent/etc/ninjasec.json
