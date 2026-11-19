variable "compartment_id" { type = string }
variable "boot_volume_ids" {
  type        = object({ utility = string, replica = string })
  description = "Existing migrated encrypted boot volumes; protect and retain before adoption."
}
