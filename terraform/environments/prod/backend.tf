terraform {
  required_version = ">= 1.10.0"
  backend "s3" {
    bucket       = "ninjasec-terraform-state-533267256700"
    key          = "prod/terraform.tfstate"
    region       = "us-east-1"
    kms_key_id   = "arn:aws:kms:us-east-1:533267256700:key/d298d19a-46c6-4fd6-bbde-df3e59bce700"
    encrypt      = true
    use_lockfile = true
  }
}
