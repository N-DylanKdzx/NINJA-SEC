output "vcn_id" { value = oci_core_vcn.network.id }
output "instance_ids" { value = { utility = oci_core_instance.utility.id, replica = oci_core_instance.replica.id } }
output "private_ips" { value = { utility = oci_core_instance.utility.private_ip, replica = oci_core_instance.replica.private_ip } }
output "load_balancer_id" { value = oci_load_balancer_load_balancer.portal.id }
output "mysql_db_system_id" { value = oci_mysql_mysql_db_system.database.id }
output "backend_set_name" { value = oci_load_balancer_backend_set.portal.name }
