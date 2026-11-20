# Production adoption only: imports pin existing resources; no blank-image deployment.
# Services and DB grants are retained on the cloned boot volumes; operational sources are in scripts/.
# TLS private keys, Vault secret values and SQL passwords are deliberately external to Terraform.

resource "oci_core_security_list" "item_0" {
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-09T22:00:27.784Z"
  }
  display_name = "ninjasec-sl-private"
  freeform_tags = {
    budget  = "zero-incremental"
    lot     = "C03"
    owner   = "oci-cli"
    project = "NINJA-SEC"
  }
  vcn_id = oci_core_vcn.network.id
  egress_security_rules {
    description      = "Bastion to staged memory-stable host SSH only"
    destination      = "10.20.10.40/32"
    destination_type = "CIDR_BLOCK"
    protocol         = "6"
    stateless        = false
    tcp_options {
      max = 22
      min = 22
    }
  }
  egress_security_rules {
    description      = "Bastion to staged memory-stable host SSH only"
    destination      = "10.20.10.41/32"
    destination_type = "CIDR_BLOCK"
    protocol         = "6"
    stateless        = false
    tcp_options {
      max = 22
      min = 22
    }
  }
  egress_security_rules {
    description      = "OCI Bastion SSH to private project VM"
    destination      = "10.20.10.212/32"
    destination_type = "CIDR_BLOCK"
    protocol         = "6"
    stateless        = false
    tcp_options {
      max = 22
      min = 22
    }
  }
  egress_security_rules {
    description      = "OCI Bastion SSH to private project VM"
    destination      = "10.20.10.36/32"
    destination_type = "CIDR_BLOCK"
    protocol         = "6"
    stateless        = false
    tcp_options {
      max = 22
      min = 22
    }
  }
  ingress_security_rules {
    description = "IPv4 Path MTU Discovery"
    protocol    = "1"
    source      = "0.0.0.0/0"
    source_type = "CIDR_BLOCK"
    stateless   = false
    icmp_options {
      code = 4
      type = 3
    }
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_network_security_group" "item_0" {
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-18T18:44:35.637Z"
  }
  display_name  = "ninjasec-wireguard-utility"
  freeform_tags = {}
  vcn_id        = oci_core_vcn.network.id
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_route_table" "item_2" {
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-09T21:59:50.262Z"
  }
  display_name = "Default Route Table for ninjasec-vcn"
  freeform_tags = {
    budget  = "zero-incremental"
    lot     = "C03"
    owner   = "oci-cli"
    project = "NINJA-SEC"
  }
  vcn_id = oci_core_vcn.network.id
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_load_balancer_load_balancer" "portal" {
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-10T23:37:38.070Z"
  }
  display_name = "ninjasec-oci-lb"
  freeform_tags = {
    component = "B5"
    project   = "NINJA-SEC"
  }
  ip_mode                      = "IPV4"
  ipv6subnet_cidr              = null
  is_delete_protection_enabled = null
  is_private                   = false
  is_request_id_enabled        = null
  network_security_group_ids   = [oci_core_network_security_group.item_1.id]
  request_id_header            = null
  security_attributes          = {}
  shape                        = "flexible"
  subnet_ids                   = [oci_core_subnet.item_0.id]
  shape_details {
    maximum_bandwidth_in_mbps = 10
    minimum_bandwidth_in_mbps = 10
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_instance" "utility" {
  async                      = null
  availability_domain        = "meXg:US-ASHBURN-AD-3"
  capacity_reservation_id    = null
  cluster_placement_group_id = null
  compartment_id             = var.compartment_id
  compute_cluster_id         = null
  dedicated_vm_host_id       = null
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-18T22:36:05.249Z"
  }
  display_name      = "ninjasec-utility-stable-01"
  extended_metadata = {}
  fault_domain      = "FAULT-DOMAIN-3"
  freeform_tags = {
    Budget  = "CPU+RAM <= USD8 for two instances /14days"
    Project = "NINJA-SEC"
    Purpose = "Memory stability migration"
  }
  instance_configuration_id           = null
  ipxe_script                         = null
  is_ai_enterprise_enabled            = null
  is_pv_encryption_in_transit_enabled = null
  metadata = {
    ssh_authorized_keys = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAA/81NAyiayoVuL2jwfSh2Dl8PUVIjfM/G2VpmdB7Hs"
    user_data           = filebase64("${path.module}/bootstrap/memory-stable.sh")
  }
  preserve_boot_volume                    = null
  preserve_data_volumes_created_at_launch = null
  security_attributes                     = {}
  shape                                   = "VM.Standard.E3.Flex"
  state                                   = "RUNNING"
  update_operation_constraint             = null
  agent_config {
    are_all_plugins_disabled = false
    is_management_disabled   = false
    is_monitoring_disabled   = false
  }
  availability_config {
    is_live_migration_preferred = false
    recovery_action             = "RESTORE_INSTANCE"
  }
  create_vnic_details {
    assign_ipv6ip             = false
    assign_private_dns_record = false
    assign_public_ip          = "false"
    defined_tags = {
      "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
      "Oracle-Tags.CreatedOn" = "2026-11-18T22:36:05.346Z"
    }
    display_name = "ninjasec-utility-stable-01"
    freeform_tags = {
      Budget  = "CPU+RAM <= USD8 for two instances /14days"
      Project = "NINJA-SEC"
      Purpose = "Memory stability migration"
    }
    hostname_label         = null
    nsg_ids                = [oci_core_network_security_group.item_0.id, oci_core_network_security_group.item_4.id, oci_core_network_security_group.item_2.id]
    private_ip             = "10.20.10.40"
    security_attributes    = {}
    skip_source_dest_check = true
    subnet_cidr            = null
    subnet_id              = oci_core_subnet.item_1.id
    vlan_id                = null
  }
  instance_options {
    are_legacy_imds_endpoints_disabled = false
  }
  launch_options {
    boot_volume_type                    = "PARAVIRTUALIZED"
    firmware                            = "UEFI_64"
    is_consistent_volume_naming_enabled = true
    is_pv_encryption_in_transit_enabled = true
    network_type                        = "PARAVIRTUALIZED"
    remote_data_volume_type             = "PARAVIRTUALIZED"
  }
  shape_config {
    baseline_ocpu_utilization = "BASELINE_1_8"
    memory_in_gbs             = 4
    nvmes                     = 0
    ocpus                     = 1
    resource_management       = null
    vcpus                     = 2
  }
  source_details {
    boot_volume_size_in_gbs         = null
    boot_volume_vpus_per_gb         = null
    is_preserve_boot_volume_enabled = false
    kms_key_id                      = null
    source_id                       = var.boot_volume_ids.utility
    source_type                     = "bootVolume"
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_network_security_group" "item_4" {
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-09T22:00:41.141Z"
  }
  display_name = "ninjasec-nsg-app"
  freeform_tags = {
    budget  = "zero-incremental"
    lot     = "C03"
    owner   = "oci-cli"
    project = "NINJA-SEC"
  }
  vcn_id = oci_core_vcn.network.id
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_network_security_group" "item_2" {
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-09T22:00:58.758Z"
  }
  display_name = "ninjasec-nsg-soc"
  freeform_tags = {
    budget  = "zero-incremental"
    lot     = "C03"
    owner   = "oci-cli"
    project = "NINJA-SEC"
  }
  vcn_id = oci_core_vcn.network.id
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_route_table" "item_1" {
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-09T22:00:04.917Z"
  }
  display_name = "ninjasec-rt-edge"
  freeform_tags = {
    budget  = "zero-incremental"
    lot     = "C03"
    owner   = "oci-cli"
    project = "NINJA-SEC"
  }
  vcn_id = oci_core_vcn.network.id
  route_rules {
    description       = null
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.item_0.id
    route_type        = "STATIC"
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_instance" "replica" {
  async                      = null
  availability_domain        = "meXg:US-ASHBURN-AD-3"
  capacity_reservation_id    = null
  cluster_placement_group_id = null
  compartment_id             = var.compartment_id
  compute_cluster_id         = null
  dedicated_vm_host_id       = null
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-18T22:36:19.859Z"
  }
  display_name      = "ninjasec-replica-stable-01"
  extended_metadata = {}
  fault_domain      = "FAULT-DOMAIN-3"
  freeform_tags = {
    Budget  = "CPU+RAM <= USD8 for two instances /14days"
    Project = "NINJA-SEC"
    Purpose = "Memory stability migration"
  }
  instance_configuration_id           = null
  ipxe_script                         = null
  is_ai_enterprise_enabled            = null
  is_pv_encryption_in_transit_enabled = null
  metadata = {
    ssh_authorized_keys = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAA/81NAyiayoVuL2jwfSh2Dl8PUVIjfM/G2VpmdB7Hs"
    user_data           = filebase64("${path.module}/bootstrap/memory-stable.sh")
  }
  preserve_boot_volume                    = null
  preserve_data_volumes_created_at_launch = null
  security_attributes                     = {}
  shape                                   = "VM.Standard.E3.Flex"
  state                                   = "RUNNING"
  update_operation_constraint             = null
  agent_config {
    are_all_plugins_disabled = false
    is_management_disabled   = false
    is_monitoring_disabled   = false
  }
  availability_config {
    is_live_migration_preferred = false
    recovery_action             = "RESTORE_INSTANCE"
  }
  create_vnic_details {
    assign_ipv6ip             = false
    assign_private_dns_record = false
    assign_public_ip          = "false"
    defined_tags = {
      "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
      "Oracle-Tags.CreatedOn" = "2026-11-18T22:36:19.937Z"
    }
    display_name = "ninjasec-replica-stable-01"
    freeform_tags = {
      Budget  = "CPU+RAM <= USD8 for two instances /14days"
      Project = "NINJA-SEC"
      Purpose = "Memory stability migration"
    }
    hostname_label         = null
    nsg_ids                = [oci_core_network_security_group.item_4.id, oci_core_network_security_group.item_2.id]
    private_ip             = "10.20.10.41"
    security_attributes    = {}
    skip_source_dest_check = false
    subnet_cidr            = null
    subnet_id              = oci_core_subnet.item_1.id
    vlan_id                = null
  }
  instance_options {
    are_legacy_imds_endpoints_disabled = false
  }
  launch_options {
    boot_volume_type                    = "PARAVIRTUALIZED"
    firmware                            = "UEFI_64"
    is_consistent_volume_naming_enabled = true
    is_pv_encryption_in_transit_enabled = true
    network_type                        = "PARAVIRTUALIZED"
    remote_data_volume_type             = "PARAVIRTUALIZED"
  }
  shape_config {
    baseline_ocpu_utilization = "BASELINE_1_8"
    memory_in_gbs             = 4
    nvmes                     = 0
    ocpus                     = 1
    resource_management       = null
    vcpus                     = 2
  }
  source_details {
    boot_volume_size_in_gbs         = null
    boot_volume_vpus_per_gb         = null
    is_preserve_boot_volume_enabled = false
    kms_key_id                      = null
    source_id                       = var.boot_volume_ids.replica
    source_type                     = "bootVolume"
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_network_security_group" "item_1" {
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-10T22:23:26.678Z"
  }
  display_name = "lb-nsg"
  freeform_tags = {
    project = "NINJA-SEC"
  }
  vcn_id = oci_core_vcn.network.id
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_mysql_mysql_db_system" "database" {
  access_mode             = "UNRESTRICTED"
  admin_password          = null # sensitive
  admin_username          = null
  availability_domain     = "meXg:US-ASHBURN-AD-3"
  compartment_id          = var.compartment_id
  configuration_id        = "ocid1.mysqlconfiguration.oc1..aaaaaaaa5a33g5cxy33cwd2egvmmyhnx5lsf5frueox3mgrnfqabdqdwio7a"
  crash_recovery          = "ENABLED"
  data_storage_size_in_gb = 50
  database_management     = "DISABLED"
  database_mode           = "READ_WRITE"
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-10T23:02:25.023Z"
  }
  description  = "NINJA-SEC private standby MySQL"
  display_name = "ninjasec-mysql-private"
  fault_domain = "FAULT-DOMAIN-1"
  freeform_tags = {
    component = "B4"
    project   = "NINJA-SEC"
  }
  hostname_label      = null
  ip_address          = "10.20.10.191"
  is_highly_available = false
  mysql_version       = "26.10.0"
  nsg_ids             = [oci_core_network_security_group.item_3.id]
  port                = 3306
  port_x              = 33060
  security_attributes = {}
  shape_name          = "MySQL.Free"
  shutdown_type       = null
  state               = "ACTIVE"
  subnet_id           = oci_core_subnet.item_1.id
  backup_policy {
    defined_tags      = {}
    freeform_tags     = {}
    is_enabled        = true
    retention_in_days = 1
    soft_delete       = "DISABLED"
    window_start_time = "00:40"
    pitr_policy {
      is_enabled = false
    }
  }
  data_storage {
    is_auto_expand_storage_enabled = false
    max_storage_size_in_gbs        = 0
  }
  deletion_policy {
    automatic_backup_retention = "RETAIN"
    final_backup               = "SKIP_FINAL_BACKUP"
    is_delete_protected        = false
  }
  encrypt_data {
    key_generation_type = "SYSTEM"
    key_id              = null
  }
  maintenance {
    maintenance_schedule_type = "REGULAR"
    version_preference        = "OLDEST"
    version_track_preference  = "FOLLOW"
    window_start_time         = "TUESDAY 06:21"
  }
  read_endpoint {
    exclude_ips                  = []
    is_enabled                   = false
    read_endpoint_hostname_label = null
    read_endpoint_ip_address     = null
  }
  secure_connections {
    certificate_generation_type = "SYSTEM"
    certificate_id              = null
  }
  source {
    backup_id      = null
    db_system_id   = null
    recovery_point = null
    source_type    = "NONE"
    source_url     = null # sensitive
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_internet_gateway" "item_0" {
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-10T22:23:23.638Z"
  }
  display_name = "ninjasec-igw"
  enabled      = true
  freeform_tags = {
    project = "NINJA-SEC"
  }
  route_table_id = null
  vcn_id         = oci_core_vcn.network.id
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_subnet" "item_1" {
  availability_domain = null
  cidr_block          = "10.20.10.0/24"
  compartment_id      = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-09T22:00:33.516Z"
  }
  dhcp_options_id = "ocid1.dhcpoptions.oc1.iad.aaaaaaaa7h5e6ucxd6pa4zlb5acmqx3lgw2gjkk7evm5lcofegs3cqe3ef3a"
  display_name    = "ninjasec-subnet-private"
  dns_label       = null
  freeform_tags = {
    budget  = "zero-incremental"
    lot     = "C03"
    owner   = "oci-cli"
    project = "NINJA-SEC"
  }
  ipv4cidr_blocks            = ["10.20.10.0/24"]
  ipv6cidr_block             = null
  ipv6cidr_blocks            = []
  prohibit_internet_ingress  = true
  prohibit_public_ip_on_vnic = true
  route_table_id             = oci_core_route_table.item_0.id
  security_list_ids          = [oci_core_security_list.item_0.id]
  vcn_id                     = oci_core_vcn.network.id
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_subnet" "item_0" {
  availability_domain = null
  cidr_block          = "10.20.1.0/24"
  compartment_id      = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-10T22:31:06.681Z"
  }
  dhcp_options_id = "ocid1.dhcpoptions.oc1.iad.aaaaaaaa7h5e6ucxd6pa4zlb5acmqx3lgw2gjkk7evm5lcofegs3cqe3ef3a"
  display_name    = "ninjasec-subnet-edge"
  dns_label       = null
  freeform_tags = {
    budget  = "zero-incremental"
    lot     = "C03"
    owner   = "oci-cli"
    project = "NINJA-SEC"
  }
  ipv4cidr_blocks            = ["10.20.1.0/24"]
  ipv6cidr_block             = null
  ipv6cidr_blocks            = []
  prohibit_internet_ingress  = false
  prohibit_public_ip_on_vnic = false
  route_table_id             = oci_core_route_table.item_1.id
  security_list_ids          = [oci_core_security_list.item_1.id]
  vcn_id                     = oci_core_vcn.network.id
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_service_gateway" "item_0" {
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-10T22:18:50.736Z"
  }
  display_name   = "ninjasec-sgw"
  freeform_tags  = {}
  route_table_id = null
  vcn_id         = oci_core_vcn.network.id
  services {
    service_id = "ocid1.service.oc1.iad.aaaaaaaam4zfmy2rjue6fmglumm3czgisxzrnvrwqeodtztg7hwa272mlfna"
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_vcn" "network" {
  cidr_block     = "10.20.0.0/16"
  cidr_blocks    = ["10.20.0.0/16"]
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-09T21:59:50.262Z"
  }
  display_name = "ninjasec-vcn"
  dns_label    = null
  freeform_tags = {
    budget  = "zero-incremental"
    lot     = "C03"
    owner   = "oci-cli"
    project = "NINJA-SEC"
  }
  ipv6private_cidr_blocks          = []
  is_ipv6enabled                   = false
  is_oracle_gua_allocation_enabled = null
  security_attributes              = {}
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_network_security_group" "item_3" {
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-09T22:00:46.770Z"
  }
  display_name = "ninjasec-nsg-db"
  freeform_tags = {
    budget  = "zero-incremental"
    lot     = "C03"
    owner   = "oci-cli"
    project = "NINJA-SEC"
  }
  vcn_id = oci_core_vcn.network.id
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_security_list" "item_2" {
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-09T21:59:50.262Z"
  }
  display_name = "Default Security List for ninjasec-vcn"
  freeform_tags = {
    budget  = "zero-incremental"
    lot     = "C03"
    owner   = "oci-cli"
    project = "NINJA-SEC"
  }
  vcn_id = oci_core_vcn.network.id
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_nat_gateway" "item_0" {
  block_traffic  = false
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-10T22:23:24.188Z"
  }
  display_name = "ninjasec-nat"
  freeform_tags = {
    project = "NINJA-SEC"
  }
  public_ip_id   = "ocid1.publicip.oc1.iad.aaaaaaaate6hrjk2f5wzhf34guu3urose3vb6zgp4hbmv67q2gjyu7jlmvaa"
  route_table_id = null
  vcn_id         = oci_core_vcn.network.id
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_route_table" "item_0" {
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-09T22:00:22.594Z"
  }
  display_name = "ninjasec-rt-private"
  freeform_tags = {
    budget  = "zero-incremental"
    lot     = "C03"
    owner   = "oci-cli"
    project = "NINJA-SEC"
  }
  vcn_id = oci_core_vcn.network.id
  route_rules {
    description       = null
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_nat_gateway.item_0.id
    route_type        = "STATIC"
  }
  route_rules {
    description       = null
    destination       = "all-iad-services-in-oracle-services-network"
    destination_type  = "SERVICE_CIDR_BLOCK"
    network_entity_id = oci_core_service_gateway.item_0.id
    route_type        = "STATIC"
  }
  route_rules {
    description       = "AWS via private utility WireGuard peer; no DRG"
    destination       = "10.10.0.0/16"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = "ocid1.privateip.oc1.iad.abuwcljtfxfkikcdpihku4ee76bzqyybkhhhfdtohsctmusycrb2bl7yj3jq"
    route_type        = "STATIC"
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_security_list" "item_1" {
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-09T22:00:10.794Z"
  }
  display_name = "ninjasec-sl-edge"
  freeform_tags = {
    budget  = "zero-incremental"
    lot     = "C03"
    owner   = "oci-cli"
    project = "NINJA-SEC"
  }
  vcn_id = oci_core_vcn.network.id
  ingress_security_rules {
    description = "IPv4 Path MTU Discovery"
    protocol    = "1"
    source      = "0.0.0.0/0"
    source_type = "CIDR_BLOCK"
    stateless   = false
    icmp_options {
      code = 4
      type = 3
    }
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_network_security_group_security_rule" "group_1_rule_0" {
  description               = "Public OCI LB listener"
  destination               = null
  destination_type          = null
  direction                 = "INGRESS"
  network_security_group_id = oci_core_network_security_group.item_1.id
  protocol                  = "6"
  source                    = "0.0.0.0/0"
  source_type               = "CIDR_BLOCK"
  stateless                 = false
  tcp_options {
    destination_port_range {
      max = 80
      min = 80
    }
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_network_security_group_security_rule" "group_3_rule_3" {
  description               = "HeatWave to AWS DB 0"
  destination               = "10.10.20.0/24"
  destination_type          = "CIDR_BLOCK"
  direction                 = "EGRESS"
  network_security_group_id = oci_core_network_security_group.item_3.id
  protocol                  = "6"
  source                    = null
  source_type               = null
  stateless                 = false
  tcp_options {
    destination_port_range {
      max = 3306
      min = 3306
    }
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_network_security_group_security_rule" "group_3_rule_1" {
  description               = "AWS APP private MySQL 0"
  destination               = null
  destination_type          = null
  direction                 = "INGRESS"
  network_security_group_id = oci_core_network_security_group.item_3.id
  protocol                  = "6"
  source                    = "10.10.10.0/24"
  source_type               = "CIDR_BLOCK"
  stateless                 = false
  tcp_options {
    destination_port_range {
      max = 3306
      min = 3306
    }
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_network_security_group_security_rule" "group_0_rule_6" {
  description               = "Forward HeatWave to AWS DB 1"
  destination               = "10.10.21.0/24"
  destination_type          = "CIDR_BLOCK"
  direction                 = "EGRESS"
  network_security_group_id = oci_core_network_security_group.item_0.id
  protocol                  = "6"
  source                    = null
  source_type               = null
  stateless                 = false
  tcp_options {
    destination_port_range {
      max = 3306
      min = 3306
    }
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_network_security_group_security_rule" "group_0_rule_0" {
  description               = "WireGuard to existing AWS router only"
  destination               = "52.5.105.205/32"
  destination_type          = "CIDR_BLOCK"
  direction                 = "EGRESS"
  network_security_group_id = oci_core_network_security_group.item_0.id
  protocol                  = "17"
  source                    = null
  source_type               = null
  stateless                 = false
  udp_options {
    destination_port_range {
      max = 51820
      min = 51820
    }
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_network_security_group_security_rule" "group_4_rule_0" {
  description               = "SSH only from OCI Bastion private endpoint"
  destination               = null
  destination_type          = null
  direction                 = "INGRESS"
  network_security_group_id = oci_core_network_security_group.item_4.id
  protocol                  = "6"
  source                    = "10.20.10.105/32"
  source_type               = "CIDR_BLOCK"
  stateless                 = false
  tcp_options {
    destination_port_range {
      max = 22
      min = 22
    }
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_network_security_group_security_rule" "group_0_rule_5" {
  description               = "Forward HeatWave to AWS DB 0"
  destination               = "10.10.20.0/24"
  destination_type          = "CIDR_BLOCK"
  direction                 = "EGRESS"
  network_security_group_id = oci_core_network_security_group.item_0.id
  protocol                  = "6"
  source                    = null
  source_type               = null
  stateless                 = false
  tcp_options {
    destination_port_range {
      max = 3306
      min = 3306
    }
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_network_security_group_security_rule" "group_3_rule_5" {
  description               = "MySQL from memory-stable private host only"
  destination               = null
  destination_type          = null
  direction                 = "INGRESS"
  network_security_group_id = oci_core_network_security_group.item_3.id
  protocol                  = "6"
  source                    = "10.20.10.40/32"
  source_type               = "CIDR_BLOCK"
  stateless                 = false
  tcp_options {
    destination_port_range {
      max = 3306
      min = 3306
    }
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_network_security_group_security_rule" "group_1_rule_1" {
  description               = "Public OCI LB listener"
  destination               = null
  destination_type          = null
  direction                 = "INGRESS"
  network_security_group_id = oci_core_network_security_group.item_1.id
  protocol                  = "6"
  source                    = "0.0.0.0/0"
  source_type               = "CIDR_BLOCK"
  stateless                 = false
  tcp_options {
    destination_port_range {
      max = 443
      min = 443
    }
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_network_security_group_security_rule" "group_0_rule_2" {
  description               = "AWS APP private MySQL 1"
  destination               = null
  destination_type          = null
  direction                 = "INGRESS"
  network_security_group_id = oci_core_network_security_group.item_0.id
  protocol                  = "6"
  source                    = "10.10.11.0/24"
  source_type               = "CIDR_BLOCK"
  stateless                 = false
  tcp_options {
    destination_port_range {
      max = 3306
      min = 3306
    }
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_network_security_group_security_rule" "group_0_rule_3" {
  description               = "HeatWave initiates private replication"
  destination               = null
  destination_type          = null
  direction                 = "INGRESS"
  network_security_group_id = oci_core_network_security_group.item_0.id
  protocol                  = "6"
  source                    = "10.20.10.191/32"
  source_type               = "CIDR_BLOCK"
  stateless                 = false
  tcp_options {
    destination_port_range {
      max = 3306
      min = 3306
    }
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_network_security_group_security_rule" "group_3_rule_2" {
  description               = "AWS APP private MySQL 1"
  destination               = null
  destination_type          = null
  direction                 = "INGRESS"
  network_security_group_id = oci_core_network_security_group.item_3.id
  protocol                  = "6"
  source                    = "10.10.11.0/24"
  source_type               = "CIDR_BLOCK"
  stateless                 = false
  tcp_options {
    destination_port_range {
      max = 3306
      min = 3306
    }
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_network_security_group_security_rule" "group_0_rule_1" {
  description               = "AWS APP private MySQL 0"
  destination               = null
  destination_type          = null
  direction                 = "INGRESS"
  network_security_group_id = oci_core_network_security_group.item_0.id
  protocol                  = "6"
  source                    = "10.10.10.0/24"
  source_type               = "CIDR_BLOCK"
  stateless                 = false
  tcp_options {
    destination_port_range {
      max = 3306
      min = 3306
    }
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_network_security_group_security_rule" "group_1_rule_3" {
  description               = "LB to migrated portal only"
  destination               = "10.20.10.40/32"
  destination_type          = "CIDR_BLOCK"
  direction                 = "EGRESS"
  network_security_group_id = oci_core_network_security_group.item_1.id
  protocol                  = "6"
  source                    = null
  source_type               = null
  stateless                 = false
  tcp_options {
    destination_port_range {
      max = 8080
      min = 8080
    }
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_network_security_group_security_rule" "group_2_rule_0" {
  description               = "Grafana instance principal to OCI Monitoring via Service Gateway"
  destination               = "all-iad-services-in-oracle-services-network"
  destination_type          = "SERVICE_CIDR_BLOCK"
  direction                 = "EGRESS"
  network_security_group_id = oci_core_network_security_group.item_2.id
  protocol                  = "6"
  source                    = null
  source_type               = null
  stateless                 = false
  tcp_options {
    destination_port_range {
      max = 443
      min = 443
    }
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_network_security_group_security_rule" "group_1_rule_2" {
  description               = "NINJA-SEC private portal origin"
  destination               = "10.20.10.36/32"
  destination_type          = "CIDR_BLOCK"
  direction                 = "EGRESS"
  network_security_group_id = oci_core_network_security_group.item_1.id
  protocol                  = "6"
  source                    = null
  source_type               = null
  stateless                 = false
  tcp_options {
    destination_port_range {
      max = 8080
      min = 8080
    }
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_network_security_group_security_rule" "group_0_rule_4" {
  description               = "Forward AWS APP to HeatWave"
  destination               = "10.20.10.191/32"
  destination_type          = "CIDR_BLOCK"
  direction                 = "EGRESS"
  network_security_group_id = oci_core_network_security_group.item_0.id
  protocol                  = "6"
  source                    = null
  source_type               = null
  stateless                 = false
  tcp_options {
    destination_port_range {
      max = 3306
      min = 3306
    }
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_network_security_group_security_rule" "group_4_rule_1" {
  description               = "MySQL private monitor validation"
  destination               = "10.20.10.191/32"
  destination_type          = "CIDR_BLOCK"
  direction                 = "EGRESS"
  network_security_group_id = oci_core_network_security_group.item_4.id
  protocol                  = "6"
  source                    = null
  source_type               = null
  stateless                 = false
  tcp_options {
    destination_port_range {
      max = 3306
      min = 3306
    }
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_network_security_group_security_rule" "group_3_rule_6" {
  description               = "MySQL from memory-stable private host only"
  destination               = null
  destination_type          = null
  direction                 = "INGRESS"
  network_security_group_id = oci_core_network_security_group.item_3.id
  protocol                  = "6"
  source                    = "10.20.10.41/32"
  source_type               = "CIDR_BLOCK"
  stateless                 = false
  tcp_options {
    destination_port_range {
      max = 3306
      min = 3306
    }
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_network_security_group_security_rule" "group_3_rule_4" {
  description               = "HeatWave to AWS DB 1"
  destination               = "10.10.21.0/24"
  destination_type          = "CIDR_BLOCK"
  direction                 = "EGRESS"
  network_security_group_id = oci_core_network_security_group.item_3.id
  protocol                  = "6"
  source                    = null
  source_type               = null
  stateless                 = false
  tcp_options {
    destination_port_range {
      max = 3306
      min = 3306
    }
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_load_balancer_listener" "ninjasec_http" {
  default_backend_set_name = oci_load_balancer_backend_set.portal.name
  hostname_names           = []
  load_balancer_id         = oci_load_balancer_load_balancer.portal.id
  name                     = "ninjasec-http"
  path_route_set_name      = null
  port                     = 80
  protocol                 = "HTTP"
  routing_policy_name      = null
  rule_set_names           = ["ninjasec_force_https"]
  connection_configuration {
    backend_tcp_proxy_protocol_options = []
    backend_tcp_proxy_protocol_version = 0
    idle_timeout_in_seconds            = "60"
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_monitoring_alarm" "ninjasec_portal_backend_unhealthy" {
  alarm_summary  = null
  body           = "El balanceador OCI detecto un backend insalubre en el portal NINJA-SEC."
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-17T06:15:37.297Z"
  }
  destinations                                  = ["ocid1.onstopic.oc1.iad.amaaaaaa3nxgmgaaxikr6t2szrwyitk7eicxdiuhkncemdewzhlm6qropqlq"]
  display_name                                  = "ninjasec-portal-backend-unhealthy"
  evaluation_slack_duration                     = "PT3M"
  freeform_tags                                 = {}
  is_enabled                                    = true
  is_notifications_per_metric_dimension_enabled = false
  message_format                                = "RAW"
  metric_compartment_id                         = var.compartment_id
  metric_compartment_id_in_subtree              = false
  namespace                                     = "oci_lbaas"
  notification_title                            = "ninjasec-portal-backend-unhealthy"
  notification_version                          = "1.X"
  pending_duration                              = "PT2M"
  query                                         = "unhealthyBackendServers[1m]{resourceId=\"ocid1.loadbalancer.oc1.iad.aaaaaaaahzdbqrm4x6y2jlunz26wjwc5rcv6ujcyhvq342pvg4d6t4whe67a\",backendSetName=\"ninjasec-standby\"}.max() > 0"
  repeat_notification_duration                  = null
  resolution                                    = "1m"
  resource_group                                = null
  rule_name                                     = "base"
  severity                                      = "CRITICAL"
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_identity_policy" "ninjasec_grafana_metrics_read" {
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-11T07:29:57.032Z"
  }
  description   = "Read-only OCI monitoring metrics for Grafana"
  freeform_tags = {}
  name          = "ninjasec-grafana-metrics-read"
  statements    = ["Allow dynamic-group ninjasec-grafana-instance to read metrics in tenancy", "Allow dynamic-group ninjasec-grafana-instance to inspect compartments in tenancy"]
  version_date  = null
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_identity_policy" "ninjasec_backup_object_writer" {
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-18T23:36:05.985Z"
  }
  description   = "Backup prefix read/create/update only; no delete; existing host identity"
  freeform_tags = {}
  name          = "ninjasec-backup-object-writer"
  statements    = ["Allow dynamic-group ninjasec-grafana-instance to manage objects in tenancy where all {target.bucket.name = 'ninjasec-backup-staging', target.object.name = 'mysql/*', any {request.permission = 'OBJECT_CREATE', request.permission = 'OBJECT_OVERWRITE', request.permission = 'OBJECT_READ'}}", "Allow dynamic-group ninjasec-grafana-instance to use ons-topics in tenancy where request.permission = 'ONS_TOPIC_PUBLISH'"]
  version_date  = null
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_identity_policy" "ninjasec_azure_mysql_backup_reader" {
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-18T23:52:56.309Z"
  }
  description   = "Azure backup runbook may read mysql objects and publish failure alerts only"
  freeform_tags = {}
  name          = "ninjasec-azure-mysql-backup-reader"
  statements    = ["Allow group ninjasec-azure-audit-reader to read objects in tenancy where all {target.bucket.name='ninjasec-backup-staging', target.object.name='mysql/*', request.permission='OBJECT_READ'}", "Allow group ninjasec-azure-audit-reader to use ons-topics in tenancy where request.permission='ONS_TOPIC_PUBLISH'"]
  version_date  = null
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_identity_policy" "ninjasec_azure_audit_reader" {
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-11T21:25:30.665Z"
  }
  description   = "Read Audit events for OCI to Azure export"
  freeform_tags = {}
  name          = "ninjasec-azure-audit-reader"
  statements    = ["Allow group ninjasec-azure-audit-reader to read audit-events in tenancy"]
  version_date  = null
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_identity_policy" "ninjasec_instance_self_command_execution" {
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-18T22:06:34.562Z"
  }
  description   = "Instance may poll and report only its own Run Command execution; no permission to create commands"
  freeform_tags = {}
  name          = "ninjasec-instance-self-command-execution"
  statements    = ["Allow dynamic-group ninjasec-recovery-instances to use instance-agent-command-execution-family in tenancy where request.instance.id=target.instance.id"]
  version_date  = null
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_identity_policy" "ninjasec_grafana_replica_reader" {
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-13T01:15:59.389Z"
  }
  description   = "Read only Grafana Azure snapshot"
  freeform_tags = {}
  name          = "ninjasec-grafana-replica-reader"
  statements    = ["Allow dynamic-group ninjasec-grafana-replica-reader to read objects in tenancy where all {target.bucket.name='ninjasec-grafana-azure-logs',target.object.name='latest.json',request.permission='OBJECT_READ'}"]
  version_date  = null
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_identity_policy" "ninjasec_mysql_nsg_principal" {
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-10T23:25:24.331Z"
  }
  description = "Network permissions for the single NINJA-SEC MySQL DB system"
  freeform_tags = {
    project = "NINJA-SEC"
  }
  name         = "ninjasec-mysql-nsg-principal"
  statements   = ["Allow any-user to {NETWORK_SECURITY_GROUP_UPDATE_MEMBERS} in tenancy where all {request.principal.type='mysqldbsystem', request.principal.id='ocid1.mysqldbsystem.oc1.iad.aaaaaaaaqvrwleeienvokku6d5uuymx5cyxzpy5vqfbtpdvufs3jwskw3spa', request.resource.compartment.id='ocid1.tenancy.oc1..aaaaaaaafm7spt5qimkhk5ofybvuxx7hmq33dcd74r6dsuhzkqbvir4qdgxq'}", "Allow any-user to {VNIC_CREATE, VNIC_UPDATE, VNIC_ASSOCIATE_NETWORK_SECURITY_GROUP, VNIC_DISASSOCIATE_NETWORK_SECURITY_GROUP} in tenancy where all {request.principal.type='mysqldbsystem', request.principal.id='ocid1.mysqldbsystem.oc1.iad.aaaaaaaaqvrwleeienvokku6d5uuymx5cyxzpy5vqfbtpdvufs3jwskw3spa', request.resource.compartment.id='ocid1.tenancy.oc1..aaaaaaaafm7spt5qimkhk5ofybvuxx7hmq33dcd74r6dsuhzkqbvir4qdgxq'}"]
  version_date = null
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_identity_policy" "ninjasec_grafana_azure_logs" {
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-12T03:44:07.749Z"
  }
  description   = "Write and read only the Grafana Azure audit snapshot"
  freeform_tags = {}
  name          = "ninjasec-grafana-azure-logs"
  statements    = ["Allow group ninjasec-azure-audit-reader to manage objects in tenancy where all {target.bucket.name='ninjasec-grafana-azure-logs',target.object.name='latest.json',request.permission in ('OBJECT_CREATE','OBJECT_OVERWRITE')}", "Allow dynamic-group ninjasec-grafana-instance to read objects in tenancy where all {target.bucket.name='ninjasec-grafana-azure-logs',target.object.name='latest.json',request.permission='OBJECT_READ'}"]
  version_date  = null
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_identity_policy" "ninjasec_oci_operators" {
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-12T03:00:38.752Z"
  }
  description   = "NINJA-SEC operators SSH via dedicated Bastion only"
  freeform_tags = {}
  name          = "ninjasec-oci-operators"
  statements    = ["Allow group ninjasec-oci-operators to read bastion in tenancy where target.bastion.ocid='ocid1.bastion.oc1.iad.amaaaaaa3nxgmgaaa6fbn3e4bcmrbb2akgog6jawbjgnoyhdamlgiyznfnwq'", "Allow group ninjasec-oci-operators to use bastion in tenancy where all {target.bastion.ocid='ocid1.bastion.oc1.iad.amaaaaaa3nxgmgaaa6fbn3e4bcmrbb2akgog6jawbjgnoyhdamlgiyznfnwq',request.permission='BASTION_USE'}", "Allow group ninjasec-oci-operators to manage bastion-session in tenancy where all {target.bastion.ocid='ocid1.bastion.oc1.iad.amaaaaaa3nxgmgaaa6fbn3e4bcmrbb2akgog6jawbjgnoyhdamlgiyznfnwq',target.bastion-session.type='port_forwarding',target.bastion-session.ip='10.20.10.36/32',target.bastion-session.port='22'}", "Allow group ninjasec-oci-operators to manage bastion-session in tenancy where all {target.bastion.ocid='ocid1.bastion.oc1.iad.amaaaaaa3nxgmgaaa6fbn3e4bcmrbb2akgog6jawbjgnoyhdamlgiyznfnwq',target.bastion-session.type='port_forwarding',target.bastion-session.ip='10.20.10.212/32',target.bastion-session.port='22'}", "Allow group ninjasec-oci-operators to read instances in tenancy", "Allow group ninjasec-oci-operators to read virtual-network-family in tenancy where request.permission in ('VCN_READ','SUBNET_READ','VNIC_READ','VNIC_ATTACHMENT_READ')"]
  version_date  = null
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_load_balancer_listener" "ninjasec_https" {
  default_backend_set_name = oci_load_balancer_backend_set.portal.name
  hostname_names           = []
  load_balancer_id         = oci_load_balancer_load_balancer.portal.id
  name                     = "ninjasec-https"
  path_route_set_name      = null
  port                     = 443
  protocol                 = "HTTP"
  routing_policy_name      = null
  rule_set_names           = []
  connection_configuration {
    backend_tcp_proxy_protocol_options = []
    backend_tcp_proxy_protocol_version = 0
    idle_timeout_in_seconds            = "60"
  }
  ssl_configuration {
    certificate_ids                   = []
    certificate_name                  = "ninjasec-ip-tls"
    cipher_suite_name                 = "oci-tls-12-ssl-cipher-suite-v3"
    has_session_resumption            = false
    protocols                         = ["TLSv1.2", "TLSv1.3"]
    server_order_preference           = "ENABLED"
    trusted_certificate_authority_ids = []
    verify_depth                      = 1
    verify_peer_certificate           = false
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_identity_dynamic_group" "ninjasec_grafana_instance" {
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-11T07:29:56.196Z"
  }
  description   = "Only the NINJA-SEC monitoring VM"
  freeform_tags = {}
  matching_rule = "ANY {instance.id = 'ocid1.instance.oc1.iad.anuwcljt3nxgmgacays7ij4hje7tqwebsgo6wm3mkpwy2cl3veji2ncwaaea', instance.id = 'ocid1.instance.oc1.iad.anuwcljt3nxgmgac3gpot2j44ddf23mngyckjnq5qqae4va7xfibbjmlrutq'}"
  name          = "ninjasec-grafana-instance"
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_load_balancer_backend_set" "portal" {
  backend_max_connections = null
  load_balancer_id        = oci_load_balancer_load_balancer.portal.id
  name                    = "ninjasec-standby"
  policy                  = "ROUND_ROBIN"
  health_checker {
    interval_ms         = 10000
    is_force_plain_text = false
    port                = 8080
    protocol            = "HTTP"
    response_body_regex = ".*"
    retries             = 3
    return_code         = 200
    timeout_in_millis   = 3000
    url_path            = "/health"
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_monitoring_alarm" "ninjasec_cpu_monitor" {
  alarm_summary  = null
  body           = "La CPU de la instancia NINJA-SEC supera el 80 %."
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-11T07:16:43.087Z"
  }
  destinations                                  = ["ocid1.onstopic.oc1.iad.amaaaaaa3nxgmgaaxikr6t2szrwyitk7eicxdiuhkncemdewzhlm6qropqlq"]
  display_name                                  = "ninjasec-cpu-monitor"
  evaluation_slack_duration                     = "PT3M"
  freeform_tags                                 = {}
  is_enabled                                    = true
  is_notifications_per_metric_dimension_enabled = false
  message_format                                = "RAW"
  metric_compartment_id                         = var.compartment_id
  metric_compartment_id_in_subtree              = false
  namespace                                     = "oci_vmi_resource_utilization"
  notification_title                            = "ninjasec-cpu-monitor"
  notification_version                          = "1.X"
  pending_duration                              = "PT1M"
  query                                         = "CpuUtilization[5m]{resourceId=\"ocid1.instance.oc1.iad.anuwcljt3nxgmgac3gpot2j44ddf23mngyckjnq5qqae4va7xfibbjmlrutq\"}.mean() > 80"
  repeat_notification_duration                  = null
  resolution                                    = "1m"
  resource_group                                = null
  rule_name                                     = "base"
  severity                                      = "WARNING"
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_identity_policy" "ninjasec_terraform_metadata_review" {
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-19T00:18:40.959Z"
  }
  description   = "Read-only Terraform planning metadata; no cloud create/update/delete or secret bundles"
  freeform_tags = {}
  name          = "ninjasec-terraform-metadata-review"
  statements    = ["Allow dynamic-group ninjasec-grafana-instance to read virtual-network-family in tenancy", "Allow dynamic-group ninjasec-grafana-instance to read instance-family in tenancy", "Allow dynamic-group ninjasec-grafana-instance to read volume-family in tenancy", "Allow dynamic-group ninjasec-grafana-instance to read mysql-family in tenancy", "Allow dynamic-group ninjasec-grafana-instance to read load-balancers in tenancy", "Allow dynamic-group ninjasec-grafana-instance to read alarms in tenancy", "Allow dynamic-group ninjasec-grafana-instance to read policies in tenancy", "Allow dynamic-group ninjasec-grafana-instance to read dynamic-groups in tenancy", "Allow dynamic-group ninjasec-grafana-instance to use network-security-groups in tenancy where request.permission = 'NETWORK_SECURITY_GROUP_LIST_SECURITY_RULES'"]
  version_date  = null
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_monitoring_alarm" "ninjasec_cpu_replica" {
  alarm_summary  = null
  body           = "La CPU de la instancia NINJA-SEC supera el 80 %."
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-11T07:16:43.087Z"
  }
  destinations                                  = ["ocid1.onstopic.oc1.iad.amaaaaaa3nxgmgaaxikr6t2szrwyitk7eicxdiuhkncemdewzhlm6qropqlq"]
  display_name                                  = "ninjasec-cpu-replica"
  evaluation_slack_duration                     = "PT3M"
  freeform_tags                                 = {}
  is_enabled                                    = true
  is_notifications_per_metric_dimension_enabled = false
  message_format                                = "RAW"
  metric_compartment_id                         = var.compartment_id
  metric_compartment_id_in_subtree              = false
  namespace                                     = "oci_vmi_resource_utilization"
  notification_title                            = "ninjasec-cpu-replica"
  notification_version                          = "1.X"
  pending_duration                              = "PT1M"
  query                                         = "CpuUtilization[5m]{resourceId=\"ocid1.instance.oc1.iad.anuwcljt3nxgmgac6suofn76uki3a25nciwdev35fvk2xk6l6lbz36dsmlrq\"}.mean() > 80"
  repeat_notification_duration                  = null
  resolution                                    = "1m"
  resource_group                                = null
  rule_name                                     = "base"
  severity                                      = "WARNING"
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_identity_policy" "ninjasec_portal_vault_read" {
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-11T07:51:25.144Z"
  }
  description   = "Portal VM reads only its MySQL application secret"
  freeform_tags = {}
  name          = "ninjasec-portal-vault-read"
  statements    = ["Allow dynamic-group ninjasec-grafana-instance to read secret-bundles in tenancy where target.secret.id = 'ocid1.vaultsecret.oc1.iad.amaaaaaa3nxgmgaax2asqrwadm6ll3uq47bzykuef263eyz3zlw6cksjv4ca'"]
  version_date  = null
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_core_network_security_group_security_rule" "group_4_rule_2" {
  description               = "NINJA-SEC private portal origin"
  destination               = null
  destination_type          = null
  direction                 = "INGRESS"
  network_security_group_id = oci_core_network_security_group.item_4.id
  protocol                  = "6"
  source                    = oci_core_network_security_group.item_1.id
  source_type               = "NETWORK_SECURITY_GROUP"
  stateless                 = false
  tcp_options {
    destination_port_range {
      max = 8080
      min = 8080
    }
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_identity_dynamic_group" "ninjasec_recovery_instances" {
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-18T22:06:34.149Z"
  }
  description   = "Only the two NINJA-SEC instances may retrieve their own authorized recovery commands"
  freeform_tags = {}
  matching_rule = "ANY {instance.id = 'ocid1.instance.oc1.iad.anuwcljt3nxgmgacays7ij4hje7tqwebsgo6wm3mkpwy2cl3veji2ncwaaea', instance.id = 'ocid1.instance.oc1.iad.anuwcljt3nxgmgac3gpot2j44ddf23mngyckjnq5qqae4va7xfibbjmlrutq', instance.id = 'ocid1.instance.oc1.iad.anuwcljt3nxgmgacy6ljbmb5iateotxlcnh5x4hl43o3ywricnav6kav3qla', instance.id = 'ocid1.instance.oc1.iad.anuwcljt3nxgmgac6suofn76uki3a25nciwdev35fvk2xk6l6lbz36dsmlrq'}"
  name          = "ninjasec-recovery-instances"
  lifecycle {
    prevent_destroy = true
  }
}

resource "oci_identity_dynamic_group" "ninjasec_grafana_replica_reader" {
  compartment_id = var.compartment_id
  defined_tags = {
    "Oracle-Tags.CreatedBy" = "default/ndylanx@gmail.com"
    "Oracle-Tags.CreatedOn" = "2026-11-13T01:15:58.417Z"
  }
  description   = "Read Grafana snapshot from replica VM"
  freeform_tags = {}
  matching_rule = "ANY {instance.id = 'ocid1.instance.oc1.iad.anuwcljt3nxgmgacy6ljbmb5iateotxlcnh5x4hl43o3ywricnav6kav3qla', instance.id = 'ocid1.instance.oc1.iad.anuwcljt3nxgmgac6suofn76uki3a25nciwdev35fvk2xk6l6lbz36dsmlrq'}"
  name          = "ninjasec-grafana-replica-reader"
  lifecycle {
    prevent_destroy = true
  }
}
