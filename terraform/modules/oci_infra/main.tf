locals {
  tags = { project = "NINJA-SEC" }
  subnets = {
    edge    = { cidr = var.edge_cidr, private = false }
    private = { cidr = var.private_cidr, private = true }
  }
  nsg_names = {
    app = "${var.name_prefix}-nsg-app"
    soc = "${var.name_prefix}-nsg-soc"
    db  = "${var.name_prefix}-nsg-db"
    lb  = "lb-nsg"
  }
}

resource "oci_core_vcn" "this" {
  compartment_id = var.compartment_id
  cidr_blocks    = [var.vcn_cidr]
  display_name   = "${var.name_prefix}-vcn"
  freeform_tags  = local.tags
}

resource "oci_core_internet_gateway" "this" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.this.id
  display_name   = "${var.name_prefix}-igw"
  enabled        = true
}

resource "oci_core_nat_gateway" "this" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.this.id
  display_name   = "${var.name_prefix}-nat"
  block_traffic  = false
}

resource "oci_core_service_gateway" "this" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.this.id
  display_name   = "${var.name_prefix}-sgw"
  services {
    service_id = var.oracle_services.id
  }
}

resource "oci_core_route_table" "edge" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.this.id
  display_name   = "${var.name_prefix}-rt-edge"
  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.this.id
  }
}

resource "oci_core_route_table" "private" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.this.id
  display_name   = "${var.name_prefix}-rt-private"
  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_nat_gateway.this.id
  }
  route_rules {
    destination       = var.oracle_services.cidr_block
    destination_type  = "SERVICE_CIDR_BLOCK"
    network_entity_id = oci_core_service_gateway.this.id
  }
}

resource "oci_core_security_list" "subnet" {
  for_each       = local.subnets
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.this.id
  display_name   = "${var.name_prefix}-sl-${each.key}"
  ingress_security_rules {
    protocol = "1"
    source   = "0.0.0.0/0"
    icmp_options {
      type = 3
      code = 4
    }
  }
}

resource "oci_core_subnet" "this" {
  for_each                   = local.subnets
  compartment_id             = var.compartment_id
  vcn_id                     = oci_core_vcn.this.id
  cidr_block                 = each.value.cidr
  display_name               = "${var.name_prefix}-subnet-${each.key}"
  prohibit_public_ip_on_vnic = each.value.private
  route_table_id             = each.value.private ? oci_core_route_table.private.id : oci_core_route_table.edge.id
  security_list_ids          = [oci_core_security_list.subnet[each.key].id]
}

resource "oci_core_network_security_group" "this" {
  for_each       = local.nsg_names
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.this.id
  display_name   = each.value
}

resource "oci_core_instance" "this" {
  for_each            = var.instances
  compartment_id      = var.compartment_id
  availability_domain = each.value.availability_domain
  display_name        = each.key
  shape               = "VM.Standard.E2.1.Micro"
  freeform_tags       = local.tags

  create_vnic_details {
    subnet_id        = oci_core_subnet.this["private"].id
    assign_public_ip = false
    private_ip       = each.value.private_ip
    nsg_ids          = [for role in each.value.nsg_roles : oci_core_network_security_group.this[role].id]
  }

  metadata = { ssh_authorized_keys = var.ssh_public_key }

  source_details {
    source_type             = "image"
    source_id               = each.value.image_id
    boot_volume_size_in_gbs = 50
  }

  is_pv_encryption_in_transit_enabled = true
}

resource "oci_mysql_mysql_db_system" "standby" {
  compartment_id          = var.compartment_id
  availability_domain     = var.mysql_availability_domain
  display_name            = "${var.name_prefix}-mysql-private"
  shape_name              = "MySQL.Free"
  data_storage_size_in_gb = 50
  subnet_id               = oci_core_subnet.this["private"].id
  admin_username          = var.mysql_admin_username
  admin_password          = var.mysql_admin_password
  port                    = 3306
  is_highly_available     = false
  freeform_tags           = local.tags
}

resource "oci_load_balancer_load_balancer" "this" {
  compartment_id             = var.compartment_id
  display_name               = "${var.name_prefix}-oci-lb"
  shape                      = "flexible"
  is_private                 = false
  subnet_ids                 = [oci_core_subnet.this["edge"].id]
  network_security_group_ids = [oci_core_network_security_group.this["lb"].id]
  freeform_tags              = local.tags

  shape_details {
    minimum_bandwidth_in_mbps = 10
    maximum_bandwidth_in_mbps = 10
  }
}
