terraform {
  required_providers {
    oci = { source = "oracle/oci" }
  }
}

variable "compartment_id" { type = string }
variable "instance_names" { type = set(string) }

data "oci_core_instances" "portal" {
  for_each       = var.instance_names
  compartment_id = var.compartment_id
  display_name   = each.value
  state          = "RUNNING"
}

output "instances" {
  value = {
    for name, result in data.oci_core_instances.portal : name => one(result.instances).id
  }
}
