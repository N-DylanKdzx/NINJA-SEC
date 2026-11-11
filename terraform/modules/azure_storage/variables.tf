variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "storage_account_name" {
  type = string

  validation {
    condition     = can(regex("^[a-z0-9]{3,24}$", var.storage_account_name))
    error_message = "The storage account name must contain 3 to 24 lowercase letters or digits."
  }
}

variable "workspace_name" {
  type = string
}

variable "lock_retention_policies" {
  description = "Lock the container retention policies permanently. Use false for disposable validation deployments."
  type        = bool
  default     = true
}
