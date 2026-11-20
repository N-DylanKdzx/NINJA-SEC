terraform {
  required_providers {
    aws = { source = "hashicorp/aws" }
  }
}

variable "asg_name" { type = string }
variable "alb_name" { type = string }
variable "database_identifier" { type = string }

data "aws_autoscaling_group" "portal" {
  name = var.asg_name
}

data "aws_lb" "portal" {
  name = var.alb_name
}

data "aws_db_instance" "portal" {
  db_instance_identifier = var.database_identifier
}

output "inventory" {
  value = {
    asg_arn = data.aws_autoscaling_group.portal.arn
    alb_arn = data.aws_lb.portal.arn
    rds_arn = data.aws_db_instance.portal.db_instance_arn
  }
}
