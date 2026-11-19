module "oci_infra" {
  source          = "../modules/oci_infra/live"
  compartment_id  = var.compartment_id
  boot_volume_ids = var.boot_volume_ids
}
