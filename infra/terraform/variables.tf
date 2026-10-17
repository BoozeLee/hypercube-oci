variable "compartment_id" {
  type        = string
  description = "Existing compartment OCID where all resources are created."
}

variable "region" {
  type        = string
  description = "OCI home region for Always Free resources."
}

variable "oci_namespace" {
  type        = string
  description = "OCI Object Storage namespace for remote state backend."
}

variable "ssh_public_key" {
  type        = string
  description = "SSH public key for the hypercube admin user."
}

variable "admin_cidr" {
  type        = string
  default     = "0.0.0.0/0"
  description = "CIDR allowed to SSH to the instance. Restrict in production."
}

variable "instance_name" {
  type        = string
  default     = "hypercube"
  description = "Display name for the instance and related resources."
}

variable "ocpus" {
  type        = number
  default     = 2
  description = "Number of OCPUs for the instance."

  validation {
    condition     = var.allow_paid || var.ocpus <= 2
    error_message = "Free tier allows a maximum of 2 OCPUs unless allow_paid=true."
  }
}

variable "memory_in_gbs" {
  type        = number
  default     = 12
  description = "Memory in GB for the instance."

  validation {
    condition     = var.allow_paid || var.memory_in_gbs <= 12
    error_message = "Free tier allows a maximum of 12 GB memory unless allow_paid=true."
  }
}

variable "boot_volume_size_in_gbs" {
  type        = number
  default     = 50
  description = "Boot volume size in GB."

  validation {
    condition     = var.boot_volume_size_in_gbs >= 47
    error_message = "Boot volume must be at least 47 GB."
  }
}

variable "allow_paid" {
  type        = bool
  default     = false
  description = "Set to true to allow paid shapes. Human must set explicitly."
}

variable "alert_email" {
  type        = string
  default     = ""
  description = "Email address for budget alerts."
}

variable "cloud_init_path" {
  type        = string
  default     = "../cloud-init/cloud-config.yaml"
  description = "Path to the cloud-init configuration file relative to Terraform."
}
