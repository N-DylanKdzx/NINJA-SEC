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

locals {
  name = "ninjasec-iac-lifecycle"
}

module "aws_infra" {
  source = "../../modules/aws_infra/sandbox"
  name   = local.name
  cidr   = "10.240.0.0/16"
}

resource "oci_core_vcn" "sandbox" {
  compartment_id = var.oci_compartment_id
  display_name   = local.name
  cidr_blocks    = ["10.241.0.0/16"]
}

resource "oci_core_subnet" "sandbox" {
  compartment_id             = var.oci_compartment_id
  display_name               = local.name
  vcn_id                     = oci_core_vcn.sandbox.id
  cidr_block                 = "10.241.0.0/24"
  prohibit_public_ip_on_vnic = true
  prohibit_internet_ingress  = true
}

resource "azurerm_resource_group" "sandbox" {
  name     = "rg-${local.name}"
  location = "westus"
}

resource "azurerm_virtual_network" "sandbox" {
  name                = local.name
  location            = azurerm_resource_group.sandbox.location
  resource_group_name = azurerm_resource_group.sandbox.name
  address_space       = ["10.242.0.0/16"]
}

output "resource_ids" {
  value = {
    aws_subnet    = module.aws_infra.subnet_id
    oci_subnet    = oci_core_subnet.sandbox.id
    azure_network = azurerm_virtual_network.sandbox.id
  }
}
