terraform {
  required_version = ">= 1.13.5"
  required_providers {
    oci = { source = "oracle/oci", version = "7.32.0" }
  }
}

provider "oci" {
  auth   = "InstancePrincipal"
  region = var.region
}
