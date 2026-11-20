"""Resolve the CloudFormation replay parameters from deployed AWS and OCI resources."""

import argparse
import ipaddress
import json

import boto3
import oci


NETWORK_RESOURCES = {
    "AppRouteTableA": ("AppRoutesA", "AWS::EC2::RouteTable"),
    "AppRouteTableB": ("AppRoutesB", "AWS::EC2::RouteTable"),
    "DbRouteTableA": ("DbRoutesA", "AWS::EC2::RouteTable"),
    "DbRouteTableB": ("DbRoutesB", "AWS::EC2::RouteTable"),
    "RouterSecurityGroup": ("RouterSecurityGroup", "AWS::EC2::SecurityGroup"),
    "AppSecurityGroup": ("AppSecurityGroup", "AWS::EC2::SecurityGroup"),
    "DbSecurityGroup": ("DbSecurityGroup", "AWS::EC2::SecurityGroup"),
    "AppNetworkAcl": ("AppAcl", "AWS::EC2::NetworkAcl"),
    "DbNetworkAcl": ("DbAcl", "AWS::EC2::NetworkAcl"),
}
SUBNETS = {
    "AppSubnetCidrA": "AppA",
    "AppSubnetCidrB": "AppB",
    "DbSubnetCidrA": "DbA",
    "DbSubnetCidrB": "DbB",
}


def stack_resources(cloudformation, name):
    return {
        item["LogicalResourceId"]: item
        for page in cloudformation.get_paginator("list_stack_resources").paginate(StackName=name)
        for item in page["StackResourceSummaries"]
        if item["ResourceStatus"] in {"CREATE_COMPLETE", "UPDATE_COMPLETE", "IMPORT_COMPLETE"}
    }


def resource_id(resources, logical_id, resource_type):
    resource = resources[logical_id]
    if resource["ResourceType"] != resource_type:
        raise ValueError(f"{logical_id} is not a {resource_type}")
    return resource["PhysicalResourceId"]


def resolve(args):
    aws = boto3.Session(profile_name=args.aws_profile, region_name=args.aws_region)
    if aws.client("sts").get_caller_identity()["Account"] != args.aws_account:
        raise ValueError("Unexpected AWS account")
    cloudformation = aws.client("cloudformation")
    network = stack_resources(cloudformation, args.network_stack)
    router = stack_resources(cloudformation, args.router_stack)
    values = {name: resource_id(network, *ref) for name, ref in NETWORK_RESOURCES.items()}
    values["WireGuardRouterInstance"] = resource_id(router, "Router", "AWS::EC2::Instance")

    ec2 = aws.client("ec2")
    vpc_id = resource_id(network, "Vpc", "AWS::EC2::VPC")
    vpc = ec2.describe_vpcs(VpcIds=[vpc_id])["Vpcs"][0]
    subnet_ids = {
        name: resource_id(network, logical, "AWS::EC2::Subnet")
        for name, logical in SUBNETS.items()
    }
    subnets = {
        s["SubnetId"]: s
        for s in ec2.describe_subnets(SubnetIds=list(subnet_ids.values()))["Subnets"]
    }
    for name, subnet_id in subnet_ids.items():
        subnet = subnets[subnet_id]
        if subnet["VpcId"] != vpc_id or subnet["MapPublicIpOnLaunch"]:
            raise ValueError(f"{name} is not a private subnet of the expected VPC")
        values[name] = subnet["CidrBlock"]
    [reservation] = ec2.describe_instances(InstanceIds=[values["WireGuardRouterInstance"]])["Reservations"]
    [instance] = reservation["Instances"]
    if instance["VpcId"] != vpc_id or values["RouterSecurityGroup"] not in {sg["GroupId"] for sg in instance["SecurityGroups"]}:
        raise ValueError("WireGuard router does not belong to the expected VPC and security group")

    oci_config = oci.config.from_file(profile_name=args.oci_profile)
    mysql = oci.mysql.DbSystemClient(oci_config).get_db_system(args.heatwave_id).data
    networking = oci.core.VirtualNetworkClient(oci_config)
    subnet = networking.get_subnet(mysql.subnet_id).data
    oci_vcn = networking.get_vcn(subnet.vcn_id).data
    oci_cidr = ipaddress.IPv4Network(oci_vcn.cidr_block)
    aws_cidrs = [ipaddress.IPv4Network(x["CidrBlock"]) for x in vpc["CidrBlockAssociationSet"]
                 if x["CidrBlockState"]["State"] == "associated"]
    if any(oci_cidr.overlaps(cidr) for cidr in aws_cidrs):
        raise ValueError("AWS and OCI network CIDRs overlap")
    if mysql.lifecycle_state != "ACTIVE" or not subnet.prohibit_public_ip_on_vnic:
        raise ValueError("HeatWave must be active in a private subnet")
    database_ip = ipaddress.IPv4Address(mysql.ip_address)
    if database_ip not in ipaddress.IPv4Network(subnet.cidr_block) or database_ip not in oci_cidr:
        raise ValueError("HeatWave IP is outside the expected OCI network")
    values["OciNetworkCidr"] = str(oci_cidr)
    values["HeatWaveHostCidr"] = f"{database_ip}/32"
    return [{"ParameterKey": name, "ParameterValue": value} for name, value in sorted(values.items())]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aws-profile")
    parser.add_argument("--aws-region", default="us-east-1")
    parser.add_argument("--aws-account", required=True)
    parser.add_argument("--network-stack", required=True)
    parser.add_argument("--router-stack", required=True)
    parser.add_argument("--oci-profile", required=True)
    parser.add_argument("--heatwave-id", required=True)
    print(json.dumps(resolve(parser.parse_args()), indent=2))


if __name__ == "__main__":
    main()
