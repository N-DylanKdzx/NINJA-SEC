"""Remove a failed HeatWave test instance left outside the isolated Terraform state."""

import argparse
import json
from pathlib import Path
import re
import time

import oci


def attributes(state, resource_type, name):
    resources = [
        instance["attributes"]
        for resource in state["resources"]
        if resource.get("module") == "module.oci_infra"
        and resource["mode"] == "managed"
        and resource["type"] == resource_type
        and resource["name"] == name
        for instance in resource["instances"]
    ]
    if len(resources) > 1:
        raise ValueError(f"More than one isolated {resource_type}.{name} in state")
    return resources[0] if resources else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state", type=Path)
    parser.add_argument("suffix")
    args = parser.parse_args()
    if not re.fullmatch(r"m105[0-9a-f]{8}", args.suffix):
        raise ValueError("Expected the suffix of the isolated M10.5 replay")
    if not args.state.is_file():
        return
    state = json.loads(args.state.read_text(encoding="utf-8"))
    if attributes(state, "oci_mysql_mysql_db_system", "standby"):
        return  # Terraform owns this database and handles its destruction.
    vcn = attributes(state, "oci_core_vcn", "this")
    subnet = attributes(state, "oci_core_subnet", "replication")
    if not subnet or not vcn:
        return  # Terraform cannot have requested the database before both exist.
    prefix = f"ninjasec-m105-{args.suffix}"
    if (vcn["display_name"] != f"{prefix}-vcn" or subnet["vcn_id"] != vcn["id"]
            or subnet["cidr_block"] != "10.244.11.0/24"
            or not subnet["prohibit_public_ip_on_vnic"]):
        raise ValueError("The state does not contain the isolated replica network")

    cfg = oci.config.from_file(profile_name="NINJA_SEC_TERRAFORM")
    cfg["region"] = "us-ashburn-1"
    mysql = oci.mysql.DbSystemClient(cfg, timeout=(5, 20))
    db_name = f"{prefix}-mysql-private"
    result = mysql.list_db_systems(
        compartment_id=cfg["tenancy"], display_name=db_name)
    remaining = [
        db for db in result.data
        if db.display_name == db_name and db.lifecycle_state != "DELETED"
    ]
    if len(remaining) > 1 or result.has_next_page:
        raise ValueError("Expected one database with the exact name of the isolated replay")
    if not remaining:
        return
    db = mysql.get_db_system(remaining[0].id).data
    if (db.compartment_id != cfg["tenancy"] or db.subnet_id != subnet["id"]
            or db.shape_name != "MySQL.2" or db.ip_address != "10.244.11.10"
            or db.endpoints or db.lifecycle_state not in {"FAILED", "DELETING"}
            or db.deletion_policy.is_delete_protected):
        raise ValueError("Only a failed database without endpoints in the isolated subnet can be removed")
    if db.lifecycle_state == "FAILED":
        response = mysql.delete_db_system(db.id)
        print("M105_ORPHAN_DELETE_REQUEST", db.id, response.request_id, flush=True)
    for _ in range(60):
        try:
            if mysql.get_db_system(db.id).data.lifecycle_state == "DELETED":
                break
        except oci.exceptions.ServiceError as error:
            if error.status == 404:
                break
            raise
        time.sleep(5)
    else:
        raise RuntimeError("Removal of the failed isolated HeatWave database could not be verified")
    print("M105_ORPHAN_REMOVED", db.id, flush=True)


if __name__ == "__main__":
    main()
