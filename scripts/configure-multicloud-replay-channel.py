"""Create or remove the native OCI replication channel for an isolated AWS/OCI replay."""

import argparse
import json
import os
import re
import ssl
import sys
import time
import urllib.request

import boto3
import oci


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remove", action="store_true")
    args = parser.parse_args()
    state = json.load(sys.stdin)
    portal = state["portal_replay"]["value"]
    azure = state["audit_replay"]["value"]
    target = state["oci_replay"]["value"]
    suffix = re.fullmatch(r"rg-ninjasec-audit-replay-([a-z0-9]{8,12})", azure["resource_group"])
    if not suffix:
        raise ValueError("The output belongs to another deployment")

    cfg = oci.config.from_file(profile_name="NINJA_SEC_TERRAFORM")
    cfg["region"] = "us-ashburn-1"
    opts = {"timeout": (5, 25)}
    mysql = oci.mysql.DbSystemClient(cfg, **opts)
    db = mysql.get_db_system(target["database_id"]).data
    net = oci.core.VirtualNetworkClient(cfg, **opts)
    subnet = net.get_subnet(db.subnet_id).data
    tag = f"ninjasec-m105-{suffix[1]}"
    if (db.display_name != f"{tag}-mysql-private" or db.shape_name != "MySQL.2"
            or subnet.vcn_id != target["vcn_id"] or subnet.cidr_block != "10.244.11.0/24"
            or db.ip_address != "10.244.11.10" or not subnet.prohibit_public_ip_on_vnic):
        raise ValueError("The OCI endpoint is outside the isolated replay")

    channels = oci.mysql.ChannelsClient(cfg, **opts)
    name = f"{tag}-replication"
    found = oci.pagination.list_call_get_all_results(
        channels.list_channels, compartment_id=db.compartment_id, display_name=name).data
    found = [item for item in found if item.lifecycle_state != "DELETED"]
    if len(found) > 1 or any(item.target.db_system_id != db.id for item in found):
        raise ValueError("Existing channel does not match the isolated target")
    if args.remove:
        if found:
            channel_id = found[0].id
            result = channels.delete_channel(channel_id)
            for _ in range(70):
                try:
                    if channels.get_channel(channel_id).data.lifecycle_state == "DELETED":
                        break
                except oci.exceptions.ServiceError as error:
                    if error.status == 404:
                        break
                    raise
                time.sleep(5)
            else:
                raise RuntimeError("Isolated channel removal could not be verified")
            print("M105_CHANNEL_REMOVED", channel_id, result.request_id, flush=True)
        return

    if db.lifecycle_state != "ACTIVE":
        raise RuntimeError("Await the isolated OCI database to become ACTIVE")
    session = boto3.Session(region_name="us-east-1")
    if session.client("sts").get_caller_identity()["Account"] != "533267256700":
        raise ValueError("Unexpected AWS account")
    [source] = session.client("rds").describe_db_instances(
        DBInstanceIdentifier="ninjasec-iac-service-demo")["DBInstances"]
    if (source["PubliclyAccessible"] or source["DBSubnetGroup"]["VpcId"] != portal["vpc_id"]
            or source["Endpoint"]["Address"] != portal["database_host"]
            or source["BackupRetentionPeriod"] < 1):
        raise ValueError("The source is outside the isolated replay or binary logging is unavailable")
    if found:
        channel_id = found[0].id
    else:
        password = os.environ["NINJASEC_REPLAY_REPL_PASSWORD"]
        if not re.fullmatch(r"Aa9![0-9a-f]{28}", password):
            raise ValueError("Invalid temporary replication credential")
        context = ssl.create_default_context(cafile=os.getenv("REQUESTS_CA_BUNDLE"))
        with urllib.request.urlopen(
            "https://truststore.pki.rds.amazonaws.com/us-east-1/us-east-1-bundle.pem",
            context=context, timeout=25,
        ) as response:
            ca = response.read().decode("ascii")
        models = oci.mysql.models
        details = models.CreateChannelDetails(
            compartment_id=db.compartment_id,
            display_name=name,
            is_enabled=True,
            source=models.CreateChannelSourceFromMysqlDetails(
                hostname=source["Endpoint"]["Address"], port=3306,
                username="ninjasec_replay_replica", password=password,
                ssl_mode="VERIFY_IDENTITY", ssl_ca_certificate=models.PemCaCertificate(contents=ca),
            ),
            target=models.CreateChannelTargetFromDbSystemDetails(
                db_system_id=db.id, channel_name="ninjasec_m105",
                filters=[models.ChannelFilter(type="REPLICATE_WILD_DO_TABLE", value="ninjasec.incidents")],
            ),
            freeform_tags={"Project": "NINJA-SEC", "Purpose": "M10.5 isolated replay"},
        )
        try:
            result = channels.create_channel(details, opc_retry_token=suffix[1])
        except oci.exceptions.ServiceError as error:
            detail = str(error.message).replace(password, "[redacted]")
            raise RuntimeError(
                f"OCI create_channel failed: {error.status} {error.code} "
                f"{error.request_id}: {detail[:600]}"
            ) from None
        channel_id = result.data.id
        print("M105_CHANNEL_CREATED", channel_id, result.request_id, flush=True)
    for _ in range(75):
        check = channels.get_channel(channel_id)
        channel = check.data
        if channel.source.hostname != portal["database_host"] or channel.source.ssl_mode != "VERIFY_IDENTITY":
            raise ValueError("The channel does not match the isolated RDS and TLS policy")
        if channel.lifecycle_state == "ACTIVE":
            print("M105_CHANNEL_ACTIVE", channel.id, check.request_id, flush=True)
            return
        if channel.lifecycle_state in {"FAILED", "DELETED", "NEEDS_ATTENTION"}:
            raise RuntimeError(f"Isolated OCI channel {channel.id} entered {channel.lifecycle_state}")
        time.sleep(8)
    raise RuntimeError(f"Isolated OCI channel {channel_id} did not become ACTIVE")


if __name__ == "__main__":
    main()
