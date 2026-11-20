terraform {
  required_version = ">= 1.13.5"
  required_providers {
    aws     = { source = "hashicorp/aws", version = "5.100.0" }
    oci     = { source = "oracle/oci", version = "7.32.0" }
    azurerm = { source = "hashicorp/azurerm", version = "4.81.0" }
  }
}

provider "aws" {
  region              = "us-east-1"
  allowed_account_ids = ["533267256700"]
}

provider "oci" {
  config_file_profile = "NINJA_SEC_TERRAFORM"
  region              = "us-ashburn-1"
}

provider "azurerm" {
  subscription_id                 = "020556eb-782f-4afc-84d3-39cd392763ba"
  resource_provider_registrations = "none"
  features {}
}

variable "oci_compartment_id" { type = string }

