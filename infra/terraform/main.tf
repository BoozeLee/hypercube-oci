terraform {
  backend "s3" {
    bucket                      = var.oci_namespace
    key                         = "terraform.tfstate"
    region                      = var.region
    endpoint                    = "https://objectstorage.${var.region}.oraclecloud.com"
    skip_region_validation      = true
    skip_credentials_validation = true
    skip_requesting_account_id  = true
    skip_s3_checksum            = true
  }
}

locals {
  common_tags = {
    Project     = "hypercube"
    ManagedBy   = "terraform"
    Environment = "always-free"
  }
}

# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------

resource "oci_core_vcn" "hypercube" {
  compartment_id = var.compartment_id
  cidr_block     = "10.0.0.0/16"
  display_name   = "${var.instance_name}-vcn"
  dns_label      = "hypercube"
  freeform_tags  = local.common_tags
}

resource "oci_core_internet_gateway" "hypercube" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.hypercube.id
  display_name   = "${var.instance_name}-igw"
  freeform_tags  = local.common_tags
}

resource "oci_core_route_table" "hypercube" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.hypercube.id
  display_name   = "${var.instance_name}-rt"
  freeform_tags  = local.common_tags

  route_rules {
    network_entity_id = oci_core_internet_gateway.hypercube.id
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
  }
}

resource "oci_core_subnet" "hypercube" {
  compartment_id    = var.compartment_id
  vcn_id            = oci_core_vcn.hypercube.id
  cidr_block        = "10.0.0.0/24"
  display_name      = "${var.instance_name}-subnet"
  dns_label         = "public"
  route_table_id    = oci_core_route_table.hypercube.id
  security_list_ids = [oci_core_security_list.hypercube.id]
  freeform_tags     = local.common_tags
}

resource "oci_core_security_list" "hypercube" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.hypercube.id
  display_name   = "${var.instance_name}-sl"
  freeform_tags  = local.common_tags

  ingress_security_rules {
    protocol    = "6" # TCP
    source      = var.admin_cidr
    source_type = "CIDR_BLOCK"
    tcp_options {
      min = 22
      max = 22
    }
    description = "SSH from admin CIDR"
  }

  egress_security_rules {
    protocol    = "all"
    destination = "0.0.0.0/0"
    description = "Allow all outbound"
  }
}

# ---------------------------------------------------------------------------
# Compute
# ---------------------------------------------------------------------------

data "oci_core_images" "ubuntu" {
  compartment_id           = var.compartment_id
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "24.04"
  shape                    = "VM.Standard.A1.Flex"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

locals {
  image_id      = data.oci_core_images.ubuntu.images[0].id
  cloud_init    = base64encode(templatefile(var.cloud_init_path, { ssh_public_key = var.ssh_public_key }))
  free_tier_tag = var.allow_paid ? "paid" : "always-free"
}

resource "oci_core_instance" "hypercube" {
  compartment_id      = var.compartment_id
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  display_name        = var.instance_name
  shape               = "VM.Standard.A1.Flex"
  freeform_tags       = merge(local.common_tags, { Tier = local.free_tier_tag })

  shape_config {
    ocpus         = var.ocpus
    memory_in_gbs = var.memory_in_gbs
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.hypercube.id
    assign_public_ip = true
  }

  source_details {
    source_type             = "image"
    source_id               = local.image_id
    boot_volume_size_in_gbs = var.boot_volume_size_in_gbs
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
    user_data           = local.cloud_init
  }

  preserve_boot_volume = false
}

data "oci_identity_availability_domains" "ads" {
  compartment_id = var.compartment_id
}

# ---------------------------------------------------------------------------
# Budget alert (tenancy-level)
# ---------------------------------------------------------------------------

resource "oci_budget_budget" "hypercube" {
  count          = var.alert_email != "" ? 1 : 0
  compartment_id = var.compartment_id
  amount         = 1
  reset_period   = "MONTHLY"
  display_name   = "${var.instance_name}-budget"
  freeform_tags  = local.common_tags
}

resource "oci_budget_alert_rule" "hypercube" {
  count          = var.alert_email != "" ? 1 : 0
  budget_id      = oci_budget_budget.hypercube[0].id
  display_name   = "${var.instance_name}-alert"
  type           = "FORECAST"
  threshold      = 80
  threshold_type = "PERCENTAGE"
  recipients     = var.alert_email
  message        = "Hypercube OCI spending forecast reached 80%."
}
