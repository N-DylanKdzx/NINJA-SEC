variable "replication_network" {
  description = "Optional dedicated subnet and routing for an isolated inbound replication target."
  type = object({
    subnet_cidr           = string
    peer_ip               = string
    database_ip           = string
    source_cidr           = string
    source_database_cidrs = set(string)
  })
  default = null
}

variable "replication_bastion_cidr" {
  description = "Private /32 of the isolated Bastion endpoint for database verification."
  type        = string
  default     = null
}

locals {
  replication_bastion_egress = (
    var.replication_network == null ? tomap({}) : tomap({
      "${var.replication_network.peer_ip}/32"     = 22
      "${var.replication_network.database_ip}/32" = 3306
    })
  )
}

data "oci_core_private_ips" "replication_peer" {
  count      = var.replication_network == null ? 0 : 1
  subnet_id  = oci_core_subnet.this["private"].id
  ip_address = var.replication_network.peer_ip

  depends_on = [oci_core_instance.this]
}

resource "oci_core_route_table" "replication" {
  count          = var.replication_network == null ? 0 : 1
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.this.id
  display_name   = "${var.name_prefix}-rt-replication"

  route_rules {
    destination       = var.replication_network.source_cidr
    destination_type  = "CIDR_BLOCK"
    network_entity_id = one(data.oci_core_private_ips.replication_peer[0].private_ips).id
  }
}

resource "oci_core_subnet" "replication" {
  count                      = var.replication_network == null ? 0 : 1
  compartment_id             = var.compartment_id
  vcn_id                     = oci_core_vcn.this.id
  display_name               = "${var.name_prefix}-subnet-replication"
  cidr_block                 = var.replication_network.subnet_cidr
  prohibit_public_ip_on_vnic = true
  prohibit_internet_ingress  = true
  route_table_id             = oci_core_route_table.replication[0].id
  security_list_ids          = [oci_core_security_list.replication[0].id]
}

# Restrict the dedicated database subnet without requiring an IAM grant for a
# newly created HeatWave resource principal to associate its VNIC with an NSG.
resource "oci_core_security_list" "replication" {
  count          = var.replication_network == null ? 0 : 1
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.this.id
  display_name   = "${var.name_prefix}-sl-replication"

  ingress_security_rules {
    protocol = "1"
    source   = "0.0.0.0/0"
    icmp_options {
      type = 3
      code = 4
    }
  }

  dynamic "ingress_security_rules" {
    for_each = var.replication_bastion_cidr == null ? [] : [var.replication_bastion_cidr]
    content {
      protocol  = "6"
      source    = ingress_security_rules.value
      stateless = false
      tcp_options {
        min = 3306
        max = 3306
      }
    }
  }

  dynamic "egress_security_rules" {
    for_each = var.replication_network.source_database_cidrs
    content {
      protocol    = "6"
      destination = egress_security_rules.value
      stateless   = false
      tcp_options {
        min = 3306
        max = 3306
      }
    }
  }
}
