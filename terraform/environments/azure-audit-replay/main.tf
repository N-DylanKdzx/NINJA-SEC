terraform {
  required_version = ">= 1.13.5"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "4.81.0" }
  }
}

variable "subscription_id" {
  type = string
}

variable "automation_location" {
  description = "Automation region with a free account slot in the target subscription."
  type        = string
  default     = "northcentralus"
}

variable "existing_automation_principal_id" {
  description = "Managed identity of the existing NINJA-SEC Automation account. Null creates an isolated account."
  type        = string
  default     = null
}

variable "suffix" {
  description = "Unique name suffix for a disposable Azure audit deployment."
  type        = string
  validation {
    condition     = can(regex("^[a-z0-9]{8,12}$", var.suffix))
    error_message = "Use 8 to 12 lowercase letters or digits."
  }
}

provider "azurerm" {
  subscription_id                 = var.subscription_id
  resource_provider_registrations = "none"
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
    storage {
      data_plane_available = false
    }
    template_deployment {
      delete_nested_items_during_deletion = false
    }
  }
}

locals {
  name               = "ninjasec-audit-replay-${var.suffix}"
  resource_group     = "rg-${local.name}"
  location           = "westus"
  storage_account    = "nsaudit${var.suffix}"
  workspace          = "law-${local.name}"
  automation_account = "aa-${local.name}"
  aws_rule           = "aws-audit-${var.suffix}"
  oci_rule           = "oci-audit-${var.suffix}"
  base_template      = jsondecode(file("${path.module}/../../../azure/audit-replay.json"))
  shared_automation  = var.existing_automation_principal_id != null
  template = merge(local.base_template, {
    resources = [for r in local.base_template.resources : r if !local.shared_automation || !startswith(r.type, "Microsoft.Automation/")]
    outputs   = { for key, value in local.base_template.outputs : key => value if !local.shared_automation || !startswith(key, "automation") }
  })
  checkpoint_scope = "${module.archive.storage_account_id}/blobServices/default/containers/pipeline-state"
}

module "archive" {
  source                  = "../../modules/azure_storage"
  resource_group_name     = local.resource_group
  location                = local.location
  storage_account_name    = local.storage_account
  workspace_name          = local.workspace
  lock_retention_policies = false
}

resource "azurerm_resource_group_template_deployment" "audit" {
  name                = local.name
  resource_group_name = local.resource_group
  deployment_mode     = "Incremental"
  template_content    = jsonencode(local.template)
  parameters_content = jsonencode({
    workspaceName               = { value = local.workspace }
    storageAccountName          = { value = local.storage_account }
    automationAccountName       = { value = local.automation_account }
    awsRuleName                 = { value = local.aws_rule }
    ociRuleName                 = { value = local.oci_rule }
    location                    = { value = local.location }
    automationLocation          = { value = var.automation_location }
    enableWebhookAuthentication = { value = false }
  })
  depends_on = [module.archive]
}

locals {
  deployment_outputs      = jsondecode(azurerm_resource_group_template_deployment.audit.output_content)
  aws_dcr_id              = local.deployment_outputs.awsDcrResourceId.value
  automation_id           = local.shared_automation ? "/subscriptions/${var.subscription_id}/resourceGroups/rg-ninjasec-compliance/providers/Microsoft.Automation/automationAccounts/ninjasec-oci-audit" : local.deployment_outputs.automationAccountResourceId.value
  automation_principal_id = local.shared_automation ? var.existing_automation_principal_id : local.deployment_outputs.automationPrincipalId.value
  access = {
    aws_archive = {
      scope = module.archive.container_ids["audit-logs-aws"]
      role  = "Storage Blob Data Reader"
    }
    checkpoint = {
      scope = local.checkpoint_scope
      role  = "Storage Blob Data Contributor"
    }
    aws_ingestion = {
      scope = local.aws_dcr_id
      role  = "Monitoring Metrics Publisher"
    }
  }
}

resource "azurerm_role_assignment" "receiver" {
  for_each                         = local.access
  scope                            = each.value.scope
  role_definition_name             = each.value.role
  principal_id                     = local.automation_principal_id
  skip_service_principal_aad_check = true
}

resource "terraform_data" "publish_receiver" {
  triggers_replace = {
    automation = local.automation_id
    dcr        = local.aws_dcr_id
    storage    = module.archive.storage_account_id
    source     = filesha256("${path.module}/../../../scripts/import-aws-audit.ps1")
    publisher  = filesha256("${path.module}/../../../scripts/publish-azure-audit-replay.py")
    directory  = abspath("${path.module}/../../..")
  }

  provisioner "local-exec" {
    when        = destroy
    command     = "python scripts/publish-azure-audit-replay.py --remove"
    working_dir = self.triggers_replace.directory
    environment = {
      NINJASEC_REPLAY_AUTOMATION = self.triggers_replace.automation
      NINJASEC_REPLAY_DCR        = self.triggers_replace.dcr
      NINJASEC_REPLAY_STORAGE    = self.triggers_replace.storage
    }
  }

  provisioner "local-exec" {
    command     = "python scripts/publish-azure-audit-replay.py"
    working_dir = abspath("${path.module}/../../..")
    environment = {
      NINJASEC_REPLAY_AUTOMATION = self.triggers_replace.automation
      NINJASEC_REPLAY_DCR        = self.triggers_replace.dcr
      NINJASEC_REPLAY_STORAGE    = self.triggers_replace.storage
    }
  }

  depends_on = [azurerm_role_assignment.receiver]
}

output "audit_replay" {
  value = {
    resource_group        = local.resource_group
    storage_account       = local.storage_account
    workspace_id          = module.archive.workspace_id
    automation_account_id = local.automation_id
    aws_dcr_id            = local.aws_dcr_id
  }
  depends_on = [terraform_data.publish_receiver]
}
