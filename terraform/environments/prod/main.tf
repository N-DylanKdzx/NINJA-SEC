module "aws_infra" {
  source              = "../../modules/aws_infra"
  asg_name            = "ninjasec-app"
  alb_name            = "ninjasec-portal"
  database_identifier = "ninjasec-mysql-primary"
}

module "oci_infra" {
  source         = "../../modules/oci_infra/inventory"
  compartment_id = "ocid1.tenancy.oc1..aaaaaaaafm7spt5qimkhk5ofybvuxx7hmq33dcd74r6dsuhzkqbvir4qdgxq"
  instance_names = ["ninjasec-utility-stable-01", "ninjasec-replica-stable-01"]
}

module "azure_storage" {
  source              = "../../modules/azure_storage/inventory"
  resource_group_name = "rg-ninjasec-compliance"
  resources = {
    storage    = { name = "ninjaseccompliance63ba", type = "Microsoft.Storage/storageAccounts" }
    workspace  = { name = "ninjasec-law", type = "Microsoft.OperationalInsights/workspaces" }
    automation = { name = "ninjasec-oci-audit", type = "Microsoft.Automation/automationAccounts" }
    aws_dcr    = { name = "ninjasec-aws-audit", type = "Microsoft.Insights/dataCollectionRules" }
    oci_dcr    = { name = "ninjasec-oci-audit", type = "Microsoft.Insights/dataCollectionRules" }
  }
}

output "inventory" {
  value = {
    aws   = module.aws_infra.inventory
    oci   = module.oci_infra.instances
    azure = module.azure_storage.resource_ids
  }
}
