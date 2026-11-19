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
  description = "Private instances keyed by display name. The active hosts use E3 Flex, 4 GB and BASELINE_1_8; require explicit sizing for flexible shapes."
  type = map(object({
    availability_domain    = string
    image_id               = optional(string)
    boot_volume_id         = optional(string)
    private_ip             = optional(string)
    nsg_roles              = set(string)
    shape                  = optional(string, "VM.Standard.E3.Flex")
    skip_source_dest_check = optional(bool, false)
    shape_config = optional(object({
      ocpus                     = number
      memory_in_gbs             = number
      baseline_ocpu_utilization = optional(string)
    }))
  }))

  validation {
    condition     = length(var.instances) <= 2 && alltrue([for vm in values(var.instances) : length(vm.nsg_roles) > 0 && length(setsubtract(vm.nsg_roles, toset(["app", "soc"]))) == 0])
    error_message = "Use up to two private instances, with app or soc NSG roles."
  }
  validation {
    condition = alltrue([for vm in values(var.instances) :
      (vm.image_id != null) != (vm.boot_volume_id != null)
    ])
    error_message = "Specify exactly one image_id or existing cloned boot_volume_id per instance."
  }
  validation {
    condition = alltrue([for vm in values(var.instances) :
      !endswith(vm.shape, ".Flex") || vm.shape_config != null
    ])
    error_message = "Flexible shapes require explicit OCPU, memory and optional baseline; do not rely on expensive provider defaults."
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

variable "disable_dnf_makecache_on" {
  description = "Oracle Linux instance names that should disable automatic DNF cache refresh on first boot."
  type        = set(string)
  default     = []
}

variable "portal_backend_alarm" {
  description = "Optional alarm for an existing backend set and Notifications topic. Import an existing alarm before applying to adopt it."
  type = object({
    load_balancer_id      = string
    backend_set_name      = string
    metric_compartment_id = string
    topic_id              = string
  })
  default = null
}
