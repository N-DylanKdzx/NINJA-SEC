variable "compartment_id" {
  type = string
}

variable "name_prefix" {
  type    = string
  default = "ninjasec"
}

variable "vcn_cidr" {
  type    = string
  default = "10.20.0.0/16"
}

variable "edge_cidr" {
  type    = string
  default = "10.20.1.0/24"
}

variable "private_cidr" {
  type    = string
  default = "10.20.10.0/24"
}

variable "oracle_services" {
  description = "Regional service ID and CIDR label from OCI ListServices."
  type = object({
    id         = string
    cidr_block = string
  })
}

variable "instances" {
  description = "Private instances keyed by their display names. Defaults to E2.1.Micro."
  type = map(object({
    availability_domain = string
    image_id            = string
    private_ip          = optional(string)
    nsg_roles           = set(string)
    shape               = optional(string, "VM.Standard.E2.1.Micro")
    shape_config = optional(object({
      ocpus         = number
      memory_in_gbs = number
    }))
  }))

  validation {
    condition     = length(var.instances) <= 2 && alltrue([for vm in values(var.instances) : length(vm.nsg_roles) > 0 && length(setsubtract(vm.nsg_roles, toset(["app", "soc"]))) == 0])
    error_message = "Use up to two private instances, with app or soc NSG roles."
  }
}

variable "mysql_shape" {
  description = "Shape of the standalone MySQL DB system."
  type        = string
  default     = "MySQL.Free"
}

variable "heatwave_cluster" {
  description = "Optional analytics cluster attached to the MySQL DB system."
  type = object({
    shape_name   = string
    cluster_size = number
  })
  default = null
}

variable "ssh_public_key" {
  description = "SSH public key only."
  type        = string
}

variable "mysql_availability_domain" {
  type = string
}

variable "mysql_admin_username" {
  type    = string
  default = "ninjaadmin"
}

variable "mysql_admin_password" {
  description = "Pass at runtime from a secret store. Protect Terraform state as sensitive."
  type        = string
  sensitive   = true
}
