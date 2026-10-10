terraform {
  required_version = ">= 1.9.0"

  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 6.21"
    }
  }
}

provider "oci" {
  region = var.region
}
