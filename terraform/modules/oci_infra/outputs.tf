output "vcn_id" {
  value = oci_core_vcn.this.id
}

output "subnet_ids" {
  value = { for name, subnet in oci_core_subnet.this : name => subnet.id }
}

output "nsg_ids" {
  value = { for name, group in oci_core_network_security_group.this : name => group.id }
}

output "instance_ids" {
  value = { for name, vm in oci_core_instance.this : name => vm.id }
}

output "mysql_id" {
  value = oci_mysql_mysql_db_system.standby.id
}

output "load_balancer_id" {
  value = oci_load_balancer_load_balancer.this.id
}
