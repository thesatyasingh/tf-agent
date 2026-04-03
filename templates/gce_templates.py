def generate_gce_main_tf(latest_version: str) -> str:
    return f"""module "gcp_instance" {{
  source = "github.com/CenturyLink/tf-modules--gcp-tf-modules//root_gce//gce?ref={latest_version}"

  instance_name                      = var.instance_name
  disk_name                          = var.disk_name
  type                               = var.type
  region                             = var.region
  zone                               = var.zone
  image                              = var.image
  environment                        = var.environment
  project_id                         = var.project_id
  subnetwork                         = var.subnetwork
  project_shared_vpc_host_project_id = var.project_shared_vpc_host_project_id
  size                               = var.size
  service_account_email              = var.service_account_email
  network_tags                       = var.network_tags
  labels                             = var.labels
  enable_secure_boot                 = var.enable_secure_boot
  enable_vtpm                        = var.enable_vtpm
  enable_integrity_monitoring        = var.enable_integrity_monitoring
  disk_type                          = var.disk_type
}}
"""

def generate_gce_provider_tf(gcs_prefix: str) -> str:
    return f"""provider "google" {{}}
terraform {{
  required_version = ">=1.4.6"

  required_providers {{
    google = {{
      source  = "hashicorp/google"
      version = ">=4.74.0"
    }}
  }}

  backend "gcs" {{
    bucket = "lumen-mm-cloud-eng-terraform"
    prefix = "{gcs_prefix}"
  }}
}}
"""

def generate_gce_tfvars(project_id: str, host_project_id: str, instance_name: str, long_env: str, 
                        disk_type: str, vm_type: str, subnetwork: str, full_image_path: str, 
                        sa_email: str, size: str, sysgen: str, zone: str) -> str:
    return f"""project_id                         = "{project_id}"
project_shared_vpc_host_project_id = "{host_project_id}"
instance_name                      = "{instance_name}"
environment                        = "{long_env}"
region                             = "us-east4"
zone                               = "{zone}"
disk_name                          = "dsk-{instance_name}"
disk_type                          = "{disk_type}"
type                               = "{vm_type}"
subnetwork                         = ["{subnetwork}"]
image                              = "{full_image_path}"
service_account_email              = "{sa_email}"
network_tags                       = ["tag-ssh-iap"]
size                               = "{size}"
labels = {{
  "env" = "{long_env}",
  "sysgen1" = "{sysgen}"
}}
enable_secure_boot          = false
enable_vtpm                 = false
enable_integrity_monitoring = false
"""

def generate_gce_variables_tf() -> str:
    return """variable "instance_name" {
  description = "The name of the vm instance"
  type        = string
  default     = ""
}

variable "disk_name" {
  description = "The name of the vm instance"
  type        = string
  default     = ""
}

variable "project_id" {
  description = "Project ID in scope"
  type        = string
}

variable "type" {
  description = "Virtual machine type"
  default     = "e2-medium"
  type        = string
}

variable "image" {
  description = "Image for virtual machine"
  default     = "ubuntu-os-cloud/ubuntu-2204-lts"
  type        = string
}

variable "subnetwork" {
  description = "list of subnetworks"
  type        = set(string)
}

variable "enable_vtpm" {
  type        = bool
  default     = false
}

variable "enable_integrity_monitoring" {
  type        = bool
  default     = false
}

variable "enable_secure_boot" {
  type        = bool
  default     = false
}

variable "project_shared_vpc_host_project_id" {
  description = "Shared VPC to use"
  type        = string
}

variable "service_account_email" {
  description = "The email address of the service account to be created and assigned to the VM"
  type        = string
}

variable "size" {
  description = "The size of the boot disk in `Gb`"
  type        = string
  default     = "20"
}

variable "environment" {
  description = "The environment in scope"
  type        = string
  default     = "dev"
}

variable "region" {
  type = string
}

variable "zone" {
  description = "Zone for virtual machine"
  default     = "us-east4-a"
  type        = string
}

variable "disk_type" {
  description = "URL of the disk type resource describing which disk type to use to create the disk"
  type        = string
  default     = "pd-ssd"
}

variable "network_tags" {
  description = "Provide network tags e.g: [\\\"tag-ssh-iap\\\"]"
  type        = list(string)
}

variable "labels" {
  description = "A map of key/value label pairs"
  type        = map(string)
}
"""

def generate_gce_terragrunt_hcl() -> str:
    return """# This configuration is made to execute Terragrunt commands in this directory and for that reason is empty
# It is kept for consistency and future use if needed.
generate "provider" {
  path      = "provider.tf"
  if_exists = "skip"
  contents  = <<EOF
  EOF
}
"""

def generate_attached_disk_tf(app_acronym: str, suffix: str, size: str, instance_name: str) -> str:
    acronym_lower = app_acronym.lower()
    return f"""resource "google_compute_disk" "{acronym_lower}_data{suffix}" {{
  project = var.project_id
  name    = "dsk-{instance_name}-data-{suffix}"
  type    = var.disk_type
  zone    = var.zone
  size    = {size}
}}

resource "google_compute_attached_disk" "{acronym_lower}_attached_disk__data{suffix}" {{
  depends_on  = [google_compute_disk.{acronym_lower}_data{suffix}, module.gcp_instance]
  project     = var.project_id
  device_name = "{acronym_lower}-data{suffix}"
  instance    = var.instance_name
  disk        = google_compute_disk.{acronym_lower}_data{suffix}.name
  zone        = var.zone
}}
"""