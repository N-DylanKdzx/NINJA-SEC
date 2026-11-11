output "resource_group_id" {
  value = azurerm_resource_group.this.id
}

output "storage_account_id" {
  value = azurerm_storage_account.this.id
}

output "container_ids" {
  value = { for name, container in azurerm_storage_container.this : name => container.resource_manager_id }
}

output "workspace_id" {
  value = azurerm_log_analytics_workspace.this.id
}
