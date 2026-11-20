locals {
  aws_database_cidrs = toset(["10.243.14.0/24", "10.243.15.0/24"])
  oci_database_host  = "10.244.11.10/32"
}

resource "aws_eip" "wireguard" {
  domain = "vpc"
  tags   = { Name = "ninjasec-m105-peer-${var.suffix}" }
}

resource "aws_security_group" "wireguard" {
  name   = "ninjasec-m105-peer-${var.suffix}"
  vpc_id = module.aws_infra.portal_replay.vpc_id
}

resource "aws_vpc_security_group_ingress_rule" "wireguard" {
  security_group_id = aws_security_group.wireguard.id
  cidr_ipv4         = "${module.oci_infra.nat_public_ip}/32"
  ip_protocol       = "udp"
  from_port         = 51820
  to_port           = 51820
}

resource "aws_vpc_security_group_egress_rule" "router_https" {
  security_group_id = aws_security_group.wireguard.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

resource "aws_vpc_security_group_egress_rule" "router_database" {
  for_each          = local.aws_database_cidrs
  security_group_id = aws_security_group.wireguard.id
  cidr_ipv4         = each.value
  ip_protocol       = "tcp"
  from_port         = 3306
  to_port           = 3306
}

resource "aws_instance" "wireguard" {
  ami                         = var.aws_app_ami
  instance_type               = "t3.micro"
  iam_instance_profile        = var.aws_portal.instance_profile
  subnet_id                   = module.aws_infra.portal_replay.router_subnet_id
  vpc_security_group_ids      = [aws_security_group.wireguard.id]
  source_dest_check           = false
  associate_public_ip_address = false

  metadata_options {
    http_tokens = "required"
  }

  credit_specification {
    cpu_credits = "standard"
  }

  tags = { Name = "ninjasec-m105-peer-${var.suffix}" }
}

resource "aws_eip_association" "wireguard" {
  allocation_id = aws_eip.wireguard.id
  instance_id   = aws_instance.wireguard.id
}

resource "aws_route_table" "database_replication" {
  vpc_id = module.aws_infra.portal_replay.vpc_id
}

resource "aws_route" "database_replication" {
  route_table_id         = aws_route_table.database_replication.id
  destination_cidr_block = local.oci_database_host
  network_interface_id   = aws_instance.wireguard.primary_network_interface_id
}

resource "aws_route_table_association" "database_replication" {
  count          = 2
  route_table_id = aws_route_table.database_replication.id
  subnet_id      = module.aws_infra.portal_replay.database_subnets[count.index]
}

resource "aws_vpc_security_group_ingress_rule" "database_from_oci" {
  security_group_id = module.aws_infra.portal_replay.database_sg_id
  cidr_ipv4         = local.oci_database_host
  ip_protocol       = "tcp"
  from_port         = 3306
  to_port           = 3306
}

resource "oci_core_network_security_group_security_rule" "peer_wireguard" {
  network_security_group_id = module.oci_infra.nsg_ids["soc"]
  direction                 = "EGRESS"
  protocol                  = "17"
  destination               = "${aws_eip.wireguard.public_ip}/32"
  destination_type          = "CIDR_BLOCK"

  udp_options {
    destination_port_range {
      min = 51820
      max = 51820
    }
  }
}

resource "oci_core_network_security_group_security_rule" "peer_database" {
  network_security_group_id = module.oci_infra.nsg_ids["soc"]
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = local.oci_database_host
  source_type               = "CIDR_BLOCK"

  tcp_options {
    destination_port_range {
      min = 3306
      max = 3306
    }
  }
}

resource "oci_core_network_security_group_security_rule" "replication_to_rds" {
  for_each                  = { for cidr in local.aws_database_cidrs : "soc-${cidr}" => cidr }
  network_security_group_id = module.oci_infra.nsg_ids["soc"]
  direction                 = "EGRESS"
  protocol                  = "6"
  destination               = each.value
  destination_type          = "CIDR_BLOCK"

  tcp_options {
    destination_port_range {
      min = 3306
      max = 3306
    }
  }
}

resource "oci_core_network_security_group_security_rule" "peer_https" {
  network_security_group_id = module.oci_infra.nsg_ids["soc"]
  direction                 = "EGRESS"
  protocol                  = "6"
  destination               = "0.0.0.0/0"
  destination_type          = "CIDR_BLOCK"

  tcp_options {
    destination_port_range {
      min = 443
      max = 443
    }
  }
}

resource "oci_bastion_bastion" "peer" {
  compartment_id               = var.oci_replay.compartment_id
  bastion_type                 = "STANDARD"
  name                         = "ninjasec-m105-${var.suffix}"
  target_subnet_id             = module.oci_infra.subnet_ids["private"]
  client_cidr_block_allow_list = [var.operator_cidr]
  max_session_ttl_in_seconds   = 1800
}

resource "oci_core_network_security_group_security_rule" "bastion_ssh" {
  network_security_group_id = module.oci_infra.nsg_ids["soc"]
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = "${oci_bastion_bastion.peer.private_endpoint_ip_address}/32"
  source_type               = "CIDR_BLOCK"
  tcp_options {
    destination_port_range {
      min = 22
      max = 22
    }
  }
}

output "wireguard" {
  value = {
    aws_peer_id  = aws_instance.wireguard.id
    aws_peer_ip  = aws_eip.wireguard.public_ip
    oci_nat_ip   = module.oci_infra.nat_public_ip
    oci_db_cidr  = local.oci_database_host
    aws_db_cidrs = local.aws_database_cidrs
    oci_bastion  = oci_bastion_bastion.peer.id
    oci_peer_ip  = "10.244.10.10"
  }
}
