terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm" }
  }
}

variable "resource_group_name" { type = string }
variable "resources" {
  type = map(object({
    name = string
    type = string
  }))
}

data "azurerm_resources" "integration" {
  for_each            = var.resources
  resource_group_name = var.resource_group_name
  name                = each.value.name
  type                = each.value.type
}

output "resource_ids" {
  value = {
    for key, result in data.azurerm_resources.integration : key => one(result.resources).id
  }
}
