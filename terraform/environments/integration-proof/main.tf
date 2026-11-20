variable "proof_suffix" {
  description = "Unique lowercase alphanumeric suffix for the disposable integration stores."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]{12}$", var.proof_suffix))
    error_message = "Use exactly 12 lowercase alphanumeric characters."
  }
}

locals {
  proof_name = "ninjasec-m105-${var.proof_suffix}"
}

removed {
  from = aws_s3_bucket.source
  lifecycle {
    destroy = false
  }
}

resource "aws_cloudformation_stack" "source" {
  name = "${local.proof_name}-source"
  template_body = jsonencode({
    AWSTemplateFormatVersion = "2010-09-09"
    Resources = {
      SourceBucket = {
        Type                = "AWS::S3::Bucket"
        DeletionPolicy      = "Retain"
        UpdateReplacePolicy = "Retain"
        Properties          = { BucketName = local.proof_name }
      }
    }
  })
}

resource "aws_s3_bucket_public_access_block" "source" {
  bucket                  = local.proof_name
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
  depends_on              = [aws_cloudformation_stack.source]
}

resource "aws_s3_bucket_server_side_encryption_configuration" "source" {
  bucket     = local.proof_name
  depends_on = [aws_cloudformation_stack.source]

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

data "oci_objectstorage_namespace" "current" {
  compartment_id = var.oci_compartment_id
}

resource "oci_objectstorage_bucket" "relay" {
  compartment_id = var.oci_compartment_id
  namespace      = data.oci_objectstorage_namespace.current.namespace
  name           = local.proof_name
  access_type    = "NoPublicAccess"
}

resource "azurerm_resource_group" "proof" {
  name     = "rg-${local.proof_name}"
  location = "westus"
}

resource "azurerm_storage_account" "destination" {
  name                            = "nsm105${var.proof_suffix}"
  resource_group_name             = azurerm_resource_group.proof.name
  location                        = azurerm_resource_group.proof.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  https_traffic_only_enabled      = true
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  shared_access_key_enabled       = false
}

resource "azurerm_storage_container" "destination" {
  name                  = "integration-proof"
  storage_account_id    = azurerm_storage_account.destination.id
  container_access_type = "private"
}

output "proof_stores" {
  value = {
    aws_bucket             = local.proof_name
    oci_namespace          = oci_objectstorage_bucket.relay.namespace
    oci_bucket             = oci_objectstorage_bucket.relay.name
    azure_storage_account  = azurerm_storage_account.destination.name
    azure_container        = azurerm_storage_container.destination.name
    azure_container_arm_id = azurerm_storage_container.destination.resource_manager_id
  }
}

data "azurerm_client_config" "current" {}

resource "azurerm_role_assignment" "proof_writer" {
  scope                = azurerm_storage_container.destination.resource_manager_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}
