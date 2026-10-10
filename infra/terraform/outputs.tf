output "instance_id" {
  description = "OCID of the created instance."
  value       = oci_core_instance.hypercube.id
}

output "public_ip" {
  description = "Public IP address of the instance."
  value       = oci_core_instance.hypercube.public_ip
}

output "availability_domain" {
  description = "Availability domain where the instance was placed."
  value       = oci_core_instance.hypercube.availability_domain
}

output "vcn_id" {
  description = "OCID of the created VCN."
  value       = oci_core_vcn.hypercube.id
}

output "subnet_id" {
  description = "OCID of the created subnet."
  value       = oci_core_subnet.hypercube.id
}
