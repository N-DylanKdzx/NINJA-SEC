"""Activate WireGuard between the isolated AWS and OCI replay routers."""

import ipaddress
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time

import boto3
import oci
from botocore.exceptions import ClientError


KEY_PATH = "/etc/wireguard/ninjasec-replay.key"
KEY_PATTERN = r"[A-Za-z0-9+/]{43}="
AWS_TUNNEL_IP = "172.29.105.1"
OCI_TUNNEL_IP = "172.29.105.2"

PREPARE = f"""
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
install -d -m 700 /etc/wireguard
if ! command -v wg >/dev/null; then
    sed -i 's|http://|https://|g' /etc/apt/sources.list.d/ubuntu.sources
    apt-get -o Acquire::Retries=4 update > /var/log/ninjasec-replay-wireguard-install.log 2>&1
    apt-get -o Acquire::Retries=4 install -y wireguard-tools >> /var/log/ninjasec-replay-wireguard-install.log 2>&1
fi
umask 077
if ! test -s {KEY_PATH}; then
    wg genkey > {KEY_PATH}
fi
chmod 600 {KEY_PATH}
wg pubkey < {KEY_PATH}
"""


def start_script(address, peer_key, allowed, endpoint=None):
    if not re.fullmatch(KEY_PATTERN, peer_key):
        raise ValueError("Invalid WireGuard public key")
    cidrs = ", ".join(str(ipaddress.IPv4Network(item)) for item in allowed)
    lines = [
        "set -euo pipefail",
        "umask 077",
        "install -d -m 700 /etc/wireguard",
        "{",
        f"  printf '[Interface]\\nAddress = {address}/30\\nListenPort = 51820\\nMTU = 1380\\nPrivateKey = '",
        f"  cat {KEY_PATH}",
        f"  printf '\\n[Peer]\\nPublicKey = {peer_key}\\nAllowedIPs = {cidrs}\\n'",
    ]
    if endpoint is not None:
        lines.append(f"  printf 'Endpoint = {ipaddress.IPv4Address(endpoint)}:51820\\nPersistentKeepalive = 15\\n'")
    lines += [
        "} > /etc/wireguard/wg0.conf",
        "printf 'net.ipv4.ip_forward=1\\n' > /etc/sysctl.d/90-ninjasec-replay.conf",
        "sysctl -p /etc/sysctl.d/90-ninjasec-replay.conf >/dev/null",
        "systemctl enable wg-quick@wg0 >/dev/null",
        "systemctl restart wg-quick@wg0",
    ]
    return "\n".join(lines)


def aws_shell(ssm, instance, script):
    for attempt in range(24):
        try:
            command = ssm.send_command(
                InstanceIds=[instance], DocumentName="AWS-RunShellScript",
                Comment="NINJA-SEC isolated replay tunnel",
                Parameters={"commands": [script], "executionTimeout": ["300"]},
            )["Command"]["CommandId"]
            break
        except ClientError as error:
            if error.response["Error"]["Code"] != "InvalidInstanceId" or attempt == 23:
                raise
            time.sleep(5)
    for _ in range(75):
        try:
            result = ssm.get_command_invocation(CommandId=command, InstanceId=instance)
        except ssm.exceptions.InvocationDoesNotExist:
            time.sleep(5)
            continue
        state = result["Status"]
        if state == "Success":
            return result["StandardOutputContent"].strip(), command
        if state not in {"Pending", "InProgress", "Delayed"}:
            raise RuntimeError(f"Isolated AWS SSM command {command} ended with {state}")
        time.sleep(5)
    raise RuntimeError(f"Isolated AWS SSM command {command} timed out")


def main():
    state = json.load(sys.stdin)
    wireguard = state["wireguard"]["value"]
    oci_replay = state["oci_replay"]["value"]
    portal = state["portal_replay"]["value"]
    group = state["audit_replay"]["value"]["resource_group"]
    match = re.fullmatch(r"rg-ninjasec-audit-replay-([a-z0-9]{8,12})", group)
    if not match:
        raise ValueError("Expected isolated replay suffix")
    suffix = match[1]
    expected_peer = f"ninjasec-m105-peer-{suffix}"
    expected_bastion = f"ninjasec-m105-{suffix}"
    if (wireguard["oci_peer_ip"] != "10.244.10.10"
            or wireguard["oci_db_cidr"] != "10.244.11.10/32"
            or set(wireguard["aws_db_cidrs"]) != {"10.243.14.0/24", "10.243.15.0/24"}):
        raise ValueError("Unexpected isolated private network parameters")
    aws = boto3.Session(region_name="us-east-1")
    if aws.client("sts").get_caller_identity()["Account"] != "533267256700":
        raise ValueError("Unexpected AWS account")
    ec2 = aws.client("ec2")
    instance_id = wireguard["aws_peer_id"]
    [reservation] = ec2.describe_instances(InstanceIds=[instance_id])["Reservations"]
    [instance] = reservation["Instances"]
    vpc = ec2.describe_vpcs(VpcIds=[portal["vpc_id"]])["Vpcs"][0]
    if (vpc["CidrBlock"] != "10.243.0.0/16" or instance["VpcId"] != vpc["VpcId"]
            or instance.get("PublicIpAddress") != wireguard["aws_peer_ip"]
            or {x["Key"]: x["Value"] for x in instance.get("Tags", [])}.get("Name") != expected_peer):
        raise ValueError("AWS peer does not match the isolated Terraform outputs")

    cfg = oci.config.from_file(profile_name="NINJA_SEC_TERRAFORM")
    cfg["region"] = "us-ashburn-1"
    client = oci.bastion.BastionClient(cfg, timeout=(5, 25))
    bastion_id = wireguard["oci_bastion"]
    bastion = client.get_bastion(bastion_id).data
    peer = oci.core.ComputeClient(cfg, timeout=(5, 25)).get_instance(oci_replay["peer"]).data
    if (bastion.name != expected_bastion or bastion.target_subnet_id != oci_replay["subnets"]["private"]
            or peer.display_name != expected_peer or peer.lifecycle_state != "RUNNING"):
        raise ValueError("OCI peer or Bastion does not match the isolated Terraform outputs")

    home = Path.home() / ".ssh"
    bastion_key = home / "ninjasec_oci_bastion_rsa"
    peer_key_path = home / "ninjasec_oci_ed25519"
    known_hosts = home / "ninjasec_oci_known_hosts"
    bastion_public = subprocess.check_output(["ssh-keygen", "-y", "-f", str(bastion_key)], text=True).strip()
    session = client.create_session(oci.bastion.models.CreateSessionDetails(
        bastion_id=bastion_id, display_name=f"ninjasec-m105-{suffix}",
        session_ttl_in_seconds=1800,
        key_details=oci.bastion.models.PublicKeyDetails(public_key_content=bastion_public),
        target_resource_details=oci.bastion.models.CreatePortForwardingSessionTargetResourceDetails(
            target_resource_private_ip_address=wireguard["oci_peer_ip"], target_resource_port=22),
    )).data
    try:
        for _ in range(45):
            if client.get_session(session.id).data.lifecycle_state == "ACTIVE":
                break
            time.sleep(4)
        else:
            raise RuntimeError("Isolated OCI Bastion session failed to activate")
        time.sleep(8)

        def oci_shell(script):
            proxy = (f'ssh -i "{bastion_key}" -o BatchMode=yes -o StrictHostKeyChecking=accept-new '
                     f'-o "UserKnownHostsFile={known_hosts}" -W %h:%p -p 22 '
                     f'{session.id}@host.bastion.us-ashburn-1.oci.oraclecloud.com')
            result = subprocess.run([
                "ssh", "-i", str(peer_key_path), "-o", f"UserKnownHostsFile={known_hosts}",
                "-o", "StrictHostKeyChecking=accept-new", "-o", "BatchMode=yes",
                "-o", "ConnectTimeout=30", "-o", f"ProxyCommand={proxy}",
                f"ubuntu@{wireguard['oci_peer_ip']}", "sudo -n bash -s",
            ], input=script, text=True, capture_output=True, timeout=360)
            if result.returncode:
                raise RuntimeError(f"Isolated OCI peer command exited {result.returncode}")
            return result.stdout.strip()

        ssm = aws.client("ssm")
        aws_key, key_command = aws_shell(ssm, instance_id, "bash -c " + shlex.quote(PREPARE))
        oci_key = oci_shell(PREPARE)
        if not all(re.fullmatch(KEY_PATTERN, key) for key in (aws_key, oci_key)):
            raise ValueError("A peer did not return a valid WireGuard public key")
        _, start_command = aws_shell(ssm, instance_id, "bash -c " + shlex.quote(start_script(
            AWS_TUNNEL_IP, oci_key, [f"{OCI_TUNNEL_IP}/32", wireguard["oci_db_cidr"]])))
        oci_shell(start_script(OCI_TUNNEL_IP, aws_key,
                               [f"{AWS_TUNNEL_IP}/32", *wireguard["aws_db_cidrs"]], wireguard["aws_peer_ip"]))
        oci_shell(f"ping -c 3 -W 5 {AWS_TUNNEL_IP}")
        handshake, proof_command = aws_shell(ssm, instance_id, "wg show wg0 latest-handshakes")
        parts = handshake.split()
        if len(parts) != 2 or parts[0] != oci_key or not 0 <= int(time.time()) - int(parts[1]) <= 120:
            raise RuntimeError("No recent authenticated WireGuard handshake")
        print("M105_TUNNEL_VERIFIED", suffix, "SSM", key_command, start_command, proof_command, flush=True)
    finally:
        client.delete_session(session.id)


if __name__ == "__main__":
    main()
