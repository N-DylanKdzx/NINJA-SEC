terraform {
  required_version = ">= 1.13.5"
  required_providers {
    aws = { source = "hashicorp/aws", version = "5.100.0" }
  }
}

provider "aws" {
  region              = "us-east-1"
  allowed_account_ids = ["533267256700"]
}

variable "enable_service_demo" {
  type    = bool
  default = false
}

variable "demo_ami_id" {
  type    = string
  default = null
}

variable "portal_replay" {
  description = "Optional replay of the NINJA-SEC application. Use an Ubuntu 24.04 x86_64 AMI."
  type = object({
    instance_profile  = string
    instance_role_arn = string
    certificate_arn   = string
    archive_path      = string
  })
  default = null
}

variable "start_portal_instances" {
  type    = bool
  default = false
}

module "aws_infra" {
  source                 = "../../modules/aws_infra/sandbox"
  name                   = "ninjasec-iac-service-demo"
  cidr                   = "10.243.0.0/16"
  enable_service_demo    = var.enable_service_demo
  demo_ami_id            = var.demo_ami_id
  portal_replay          = var.portal_replay
  start_portal_instances = var.start_portal_instances
}

output "portal_replay" {
  value = module.aws_infra.portal_replay
}

output "service_demo" {
  value = module.aws_infra.service_demo
}
