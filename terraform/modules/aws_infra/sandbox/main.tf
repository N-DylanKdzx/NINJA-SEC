terraform {
  required_providers {
    aws = { source = "hashicorp/aws" }
  }
}

variable "name" { type = string }
variable "cidr" { type = string }

resource "aws_vpc" "sandbox" {
  cidr_block = var.cidr
  tags       = { Name = var.name, Purpose = "IaC lifecycle test" }
}

resource "aws_subnet" "sandbox" {
  vpc_id                  = aws_vpc.sandbox.id
  cidr_block              = cidrsubnet(var.cidr, 8, 0)
  map_public_ip_on_launch = false
  tags                    = { Name = var.name }
}

output "subnet_id" {
  value = aws_subnet.sandbox.id
}
