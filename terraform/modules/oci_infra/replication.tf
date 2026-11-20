variable "replication_network" {
  description = "Optional dedicated subnet and routing for an isolated inbound replication target."
  type = object({
    subnet_cidr = string
    peer_ip     = string
    database_ip = string
    source_cidr = string
  })
  default = null
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
  security_list_ids          = [oci_core_security_list.subnet["private"].id]
}
