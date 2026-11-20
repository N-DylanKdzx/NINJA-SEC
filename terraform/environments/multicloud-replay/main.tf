terraform {
  required_version = ">= 1.13.5"
  required_providers {
    aws = { source = "hashicorp/aws", version = "5.100.0" }
    oci = { source = "oracle/oci", version = "7.32.0" }
  }
}

provider "aws" {
  region              = "us-east-1"
  allowed_account_ids = ["533267256700"]
}

provider "oci" {
  region              = "us-ashburn-1"
  config_file_profile = "NINJA_SEC_TERRAFORM"
}

variable "suffix" {
  type = string
  validation {
    condition     = can(regex("^[a-z0-9]{8,12}$", var.suffix))
    error_message = "Use 8 to 12 lowercase letters or digits."
  }
}

variable "aws_app_ami" {
  type = string
}

variable "aws_portal" {
  type = object({
    instance_profile  = string
    instance_role_arn = string
    certificate_arn   = string
    archive_path      = string
  })
}

variable "start_portal_instances" {
  type    = bool
  default = false
}

variable "oci_replay" {
  type = object({
    compartment_id      = string
    availability_domain = string
    router_image_id     = string
    ssh_public_key      = string
    regional_services   = object({ id = string, cidr_block = string })
  })
}

variable "oci_mysql_admin_password" {
  description = "Temporary database password. Keep local Terraform state private."
  type        = string
  sensitive   = true
  nullable    = false

  validation {
    condition = (
      length(var.oci_mysql_admin_password) >= 8 &&
      length(var.oci_mysql_admin_password) <= 32 &&
      can(regex("[A-Z]", var.oci_mysql_admin_password)) &&
      can(regex("[a-z]", var.oci_mysql_admin_password)) &&
      can(regex("[0-9]", var.oci_mysql_admin_password)) &&
      can(regex("[^A-Za-z0-9[:space:]]", var.oci_mysql_admin_password))
    )
    error_message = "Use 8 to 32 characters with at least one uppercase letter, lowercase letter, digit, and non-alphanumeric character."
  }
}

variable "azure_subscription_id" {
  type = string
}

variable "azure_automation_principal_id" {
  description = "Managed identity of the explicitly reused NINJA-SEC Automation account."
  type        = string
}

variable "operator_cidr" {
  description = "IPv4 /32 allowed to access the isolated OCI Bastion."
  type        = string
  validation {
    condition     = can(cidrnetmask(var.operator_cidr)) && endswith(var.operator_cidr, "/32")
    error_message = "Pass the operator's IPv4 /32."
  }
}

module "aws_infra" {
  source                      = "../../modules/aws_infra/sandbox"
  name                        = "ninjasec-iac-service-demo"
  cidr                        = "10.243.0.0/16"
  enable_service_demo         = true
  enable_database_replication = true
  demo_ami_id                 = var.aws_app_ami
  portal_replay               = var.aws_portal
  start_portal_instances      = var.start_portal_instances
}

module "oci_infra" {
  source                    = "../../modules/oci_infra"
  compartment_id            = var.oci_replay.compartment_id
  name_prefix               = "ninjasec-m105-${var.suffix}"
  vcn_cidr                  = "10.244.0.0/16"
  edge_cidr                 = "10.244.1.0/24"
  private_cidr              = "10.244.10.0/24"
  oracle_services           = var.oci_replay.regional_services
  ssh_public_key            = var.oci_replay.ssh_public_key
  mysql_shape               = "MySQL.2"
  mysql_availability_domain = var.oci_replay.availability_domain
  mysql_admin_password      = var.oci_mysql_admin_password
  replication_network = {
    subnet_cidr           = "10.244.11.0/24"
    peer_ip               = "10.244.10.10"
    database_ip           = "10.244.11.10"
    source_cidr           = "10.243.0.0/16"
    source_database_cidrs = local.aws_database_cidrs
  }
  replication_bastion_cidr = "${oci_bastion_bastion.peer.private_endpoint_ip_address}/32"
  instances = {
    "ninjasec-m105-peer-${var.suffix}" = {
      availability_domain    = var.oci_replay.availability_domain
      image_id               = var.oci_replay.router_image_id
      private_ip             = "10.244.10.10"
      nsg_roles              = ["soc"]
      skip_source_dest_check = true
      shape_config = {
        ocpus                     = 1
        memory_in_gbs             = 4
        baseline_ocpu_utilization = "BASELINE_1_8"
      }
    }
  }
}

module "azure_audit" {
  source                           = "../azure-audit-replay"
  subscription_id                  = var.azure_subscription_id
  suffix                           = var.suffix
  existing_automation_principal_id = var.azure_automation_principal_id
}

output "service_demo" {
  value = module.aws_infra.service_demo
}

output "portal_replay" {
  value = module.aws_infra.portal_replay
}

output "oci_replay" {
  value = {
    vcn_id      = module.oci_infra.vcn_id
    subnets     = module.oci_infra.subnet_ids
    nsgs        = module.oci_infra.nsg_ids
    peer        = one(values(module.oci_infra.instance_ids))
    database_id = module.oci_infra.mysql_id
  }
}

output "audit_replay" {
  value = module.azure_audit.audit_replay
}
