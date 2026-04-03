def generate_provider_tf(long_env: str, domain: str, app: str, short_env: str, module: str) -> str:
    """Generates the provider.tf with the dynamic GCS backend prefix."""
    return f"""provider "google" {{}}

terraform {{
  required_version = ">= 1.3.2"

  required_providers {{
    google = {{
      source  = "hashicorp/google"
      version = ">= 4.33.0"
    }}
  }}

  backend "gcs" {{
    bucket = "lumen-infra-terraform"
    prefix = "root-lz/{long_env}/svc-{long_env}-{domain}/{long_env}-{app.lower()}/gcp-prj-{app.lower()}-{short_env}-01/{module}"
  }}
}}
"""

def generate_terragrunt_hcl() -> str:
    """Generates the identical terragrunt.hcl file used in all modules."""
    return """# This configuration is made to execute Terragrunt commands in this directory and for that reason is empty
# It is kept for consistency and future use if needed.
generate "provider" {
  path      = "provider.tf"
  if_exists = "skip"
  contents  = <<EOF
  EOF
}
"""

def generate_project_tfvars(app: str, short_env: str, project_folder_id: str, cms: dict, tags_tmplver: str) -> str:
    """Generates the terraform.tfvars for the 'project' module."""
    project_id = f"gcp-prj-{app.lower()}-{short_env}-01"
    
    return f"""project_id                  = "{project_id}"
project_folder_id           = "{project_folder_id}"
project_locations_allowed   = ["us-east4", "us-central1"]
append_google_apis          = ["vmmigration.googleapis.com", "servicemanagement.googleapis.com", "servicecontrol.googleapis.com", "iam.googleapis.com", "cloudresourcemanager.googleapis.com", "compute.googleapis.com"]
tags_app_id                 = "{cms.get('tags_app_id', '')}"
tags_cost_app_owner_tech    = "{cms.get('tags_cost_app_owner_tech', '')}"
tags_cost_app_owner_manager = "{cms.get('tags_cost_app_owner_manager', '')}"
tags_cost_budget_owner      = "{cms.get('tags_cost_budget_owner', '')}"
tags_cost_vp                = "ranga_chakravarthula__aa73727"
tags_cost_cost_center       = "{cms.get('tags_cost_cost_center', '')}"
tags_cost_region            = "north_america"
tags_costdivision           = "{cms.get('tags_costdivision', '')}"
tags_costallocation         = "chargeback"
tags_environment            = "{cms.get('tags_environment', '')}"
tags_costbaseline           = "{cms.get('tags_costbaseline', '')}"
tags_tmplver                = "{tags_tmplver}"
"""

def generate_budget_tfvars(app: str, short_env: str, budget_email: str) -> str:
    """Generates the terraform.tfvars for the 'project-budget' module."""
    project_id = f"gcp-prj-{app.lower()}-{short_env}-01"
    return f"""project_id            = "{project_id}"
project_budget_amount = "1000"
project_budget_email  = "{budget_email}"
"""

def generate_policies_tfvars(app: str, short_env: str) -> str:
    """Generates the terraform.tfvars for the 'project-policies' module."""
    project_id = f"gcp-prj-{app.lower()}-{short_env}-01"
    return f"""project_id                               = "{project_id}"
project_apply_vpc_service_control_policy = false
project_locations_allowed                = ["us-east4", "us-central1"]
"""

def generate_iam_tfvars(app: str, short_env: str) -> str:
    """Generates the terraform.tfvars for the 'iam' module."""
    project_id = f"gcp-prj-{app.lower()}-{short_env}-01"
    return f"""project_id      = "{project_id}"
project_id_m2vm = "gcp-prj-m2vm-prod-01"
"""

# ==========================================
# STATIC FILE GENERATORS
# ==========================================
# (You will paste your exact Terraform blocks into these functions)

def get_static_project_main_tf(module_version: str) -> str:
    return f"""module "project" {{
  source = "github.com/CenturyLink/tf-modules--gcp-tf-modules//prj/project?ref={module_version}"
  project_billing_id                     = var.project_billing_id
  project_id                             = var.project_id
  project_display_name                   = var.project_display_name
  project_folder_id                      = var.project_folder_id
  project_make_host_project              = var.project_make_host_project
  project_locations_allowed              = var.project_locations_allowed
  project_use_shared_vpc                 = var.project_use_shared_vpc
  project_shared_vpc_host_project_id     = var.project_shared_vpc_host_project_id
  project_use_lumen_net_infra_shared_vpc = var.project_use_lumen_net_infra_shared_vpc
  use_gce                                = var.use_gce
  google_apis                            = var.google_apis
  append_google_apis                     = var.append_google_apis
  tags_app_id                            = var.tags_app_id
  tags_cost_app_owner_tech               = var.tags_cost_app_owner_tech
  tags_cost_app_owner_manager            = var.tags_cost_app_owner_manager
  tags_cost_budget_owner                 = var.tags_cost_budget_owner
  tags_cost_cost_center                  = var.tags_cost_cost_center
  tags_cost_region                       = var.tags_cost_region
  tags_cost_vp                           = var.tags_cost_vp
  tags_costallocation                    = var.tags_costallocation
  tags_costdivision                      = var.tags_costdivision
  tags_environment                       = var.tags_environment
  tags_appfunction                       = var.tags_appfunction
  tags_costbaseline                      = var.tags_costbaseline
  tags_tmplver                           = var.tags_tmplver
}}"""

def get_static_project_variables_tf() -> str:
    return """variable "project_id" {
  description = "Pick a Project ID"
  type        = string
}

variable "project_billing_id" {
  description = "Billing ID to attach project to"
  type        = string
  default     = null
}

variable "project_folder_id" {
  description = "Folder ID to attach project to"
  type        = string
}

# variable "project_labels" {
#   description = "Map of labels for project"
#   type        = map(string)
#   default     = {}
# }

variable "project_use_lumen_net_infra_shared_vpc" {
  type        = bool
  description = "use old on prem connectivity with MPLS"
  default     = false
}

variable "project_make_host_project" {
  type        = bool
  description = "Create the project as a host project"
  default     = false
}

variable "tags_app_id" {
  description = "application identifier"
  type        = string
  validation {
    condition     = length(var.tags_app_id) > 4
    error_message = "The application id must be defined and longer than 4 characters"
  }
}

variable "tags_cost_app_owner_tech" {
  description = "Cost Application Owner Technical"
  type        = string
  validation {
    condition     = (length(var.tags_cost_app_owner_tech) > 4 && length(regex("__", var.tags_cost_app_owner_tech)) == 2)
    error_message = "The cost application technical owner must be defined and be formatted like john_doe__cuid"
  }
}

variable "tags_cost_app_owner_manager" {
  description = "Cost Application Owner Manager"
  type        = string
  validation {
    condition     = (length(var.tags_cost_app_owner_manager) > 4 && length(regex("__", var.tags_cost_app_owner_manager)) == 2)
    error_message = "The cost application owner manager must be defined and be formatted like john_doe__cuid"
  }
}

variable "tags_cost_budget_owner" {
  description = "Cost Budget Owner "
  type        = string
  validation {
    condition     = (length(var.tags_cost_budget_owner) > 4 && length(regex("__", var.tags_cost_budget_owner)) == 2)
    error_message = "The cost budget owner must be defined and be formatted like john_doe__cuid"
  }
}

variable "tags_cost_vp" {
  description = "Cost VP"
  type        = string
  validation {
    condition     = (length(var.tags_cost_vp) > 4 && length(regex("__", var.tags_cost_vp)) == 2)
    error_message = "The cost vp must be defined and be formatted like john_doe__cuid"
  }
}
variable "tags_cost_cost_center" {
  description = "Cost Center for the application"
  type        = string
  validation {
    condition     = length(var.tags_cost_cost_center) > 4
    error_message = "The cost center must be defined and longer than 4 characters"
  }
}

variable "tags_cost_region" {
  description = "The cost center region"
  type        = string
  validation {
    condition     = (length(var.tags_cost_region) >= 4)
    error_message = "The cost center region must be defined and at least 4 characters"
  }
}

variable "tags_costdivision" {
  description = "The cost division of the VP for the application"
  type        = string
  validation {
    condition     = (length(var.tags_costdivision) >= 4)
    error_message = "The cost division must be defined"
  }
}

variable "tags_costallocation" {
  description = "The cost allocation of the application: selfpay, chargeback, sptcentral, sharedcosts"
  type        = string
  validation {
    condition     = ((var.tags_costallocation == "selfpay") || (var.tags_costallocation == "chargeback") || (var.tags_costallocation == "sptcentral") || (var.tags_costallocation == "sharedcosts"))
    error_message = "The costallocation must be one of selfpay, chargeback, sptcentral or sharedcosts"
  }
}

# Add QA - 2023-03-28
variable "tags_environment" {
  description = "The environment: sandbox, dev, test, prod, shared, qa"
  type        = string
  validation {
    condition     = ((var.tags_environment == "sandbox") || (var.tags_environment == "dev") || (var.tags_environment == "test") || (var.tags_environment == "prod") || (var.tags_environment == "shared") || (var.tags_environment == "qa") || (var.tags_environment == "nonprod"))
    error_message = "The environment must be defined and one of sandbox, dev, test, prod, shared, qa"
  }
}

variable "tags_appfunction" {
  description = "The appfunction s required if costallocation is sharedcosts - an item from the defined pick list in ccoe sharepoint"
  type        = string
  default     = "n/a"
  #  validation {
  #	condition = ((var.tags_costallocation == "sharedcosts") && (var.tags_appfunction != "n/a"))
  #	error_message = "The appfunction must be defined with a costallocation of sharedcosts"
  #  }
}

variable "tags_costbaseline" {
  description = "cost baseline - when was the project created - YYYY only"
  type        = string
  default     = null
}

variable "tags_tmplver" {
  description = "project template version"
  type        = string
  default     = null
}

variable "project_display_name" {
  description = "The name to display for the project. default is project_id"
  type        = string
  default     = null
}

# variable "project_locations_restrict" {
#   description = "restrict regions for the project to deploy resources into"
#   type        = bool
#   default     = true
# }

variable "project_locations_allowed" {
  description = "allowed regions for the project to deploy resources into"
  type        = list(any)
  default     = []
}

variable "project_shared_vpc_host_project_id" {
  description = "The Shared VPC host project id"
  type        = string
  default     = null
}

variable "project_use_shared_vpc" {
  description = "flag to determine if any shared vpc is used, defaults to true"
  type        = bool
  default     = true
}

variable "use_gce" {
  description = "Does the project use GCE"
  type        = bool
  default     = true
}

variable "google_apis" {
  description = "set of google apis to not destroy"
  type        = list(string)
  default     = []
}

variable "append_google_apis" {
  description = "append apis to default set to not destroy"
  type        = list(string)
  default     = []
}
"""

def get_static_budget_main_tf(module_version: str) -> str:
    return f"""module "prj_budget" {{
  source = "github.com/CenturyLink/tf-modules--gcp-tf-modules//prj/budget?ref={module_version}"
  project_id            = var.project_id
  project_billing_id    = var.project_billing_id
  project_budget_email  = var.project_budget_email
  project_budget_amount = var.project_budget_amount
}}"""

def get_static_policies_main_tf(module_version: str) -> str:
    return f"""module "project-policies" {{
  source = "github.com/CenturyLink/tf-modules--gcp-tf-modules//prj/policies?ref={module_version}"
  project_id                                             = var.project_id
  project_deploy_cloudarmor_policy                       = var.project_deploy_cloudarmor_policy
  project_use_lumen_net_infra_shared_vpc                 = var.project_use_lumen_net_infra_shared_vpc
  project_apply_vpc_service_control_policy               = var.project_apply_vpc_service_control_policy
  project_override_vpc_service_control_policy_use_dryrun = var.project_override_vpc_service_control_policy_use_dryrun
  project_override_vpc_service_control_policy            = var.project_override_vpc_service_control_policy
  project_locations_allowed                              = var.project_locations_allowed
  use_gce                                                = var.use_gce
  patch_deployment_day_of_week                           = var.patch_deployment_day_of_week
  patch_deployment_hour_of_day                           = var.patch_deployment_hour_of_day
  patch_deployment_minute_of_day                         = var.patch_deployment_minute_of_day
  patch_schedule_type                                    = var.patch_schedule_type
  patch_deployment_week_ordinal                          = var.patch_deployment_week_ordinal
}}"""

# 3. Add the IAM static files
def get_static_iam_data_tf() -> str:
    return """data "google_iam_role" "viewer" {
  name = "roles/viewer"
}

data "google_iam_role" "sm_secret_accessor" {
  name = "roles/secretmanager.secretAccessor"
}

data "google_iam_role" "iam_serviceAccountUser" {
  name = "roles/iam.serviceAccountUser"
}

data "google_iam_role" "compute_admin" {
  name = "roles/compute.admin"
}

data "google_iam_role" "compute_net_user" {
  name = "roles/compute.networkUser"
}
data "google_iam_role" "compute_oslogin" {
  name = "roles/compute.osLogin"
}

data "google_iam_role" "svc_acct_token_creator" {
  name = "roles/iam.serviceAccountTokenCreator"
}

data "google_iam_role" "svc_acct_user" {
  name = "roles/iam.serviceAccountUser"
}

data "google_iam_role" "iam_admin" {
  name = "roles/resourcemanager.projectIamAdmin"
}
data "google_iam_role" "compute_viewer" {
  name = "roles/compute.viewer"
}

data "google_iam_role" "vmmigration_serviceAgent" {
  name = "roles/vmmigration.serviceAgent"
}

data "google_iam_role" "sm_secret_version_mgr" {
  name = "roles/secretmanager.secretVersionManager"
}

data "google_iam_role" "techsupport_editor" {
  name = "roles/cloudsupport.techSupportEditor"
}

data "google_iam_role" "log_config_writer" {
  name = "roles/logging.configWriter"
}

data "google_iam_role" "log_viewer" {
  name = "roles/logging.viewer"
}

data "google_iam_role" "mon_alt_policy_edt" {
  name = "roles/monitoring.alertPolicyEditor"
}

data "google_iam_role" "mon_edt" {
  name = "roles/monitoring.editor"
}

data "google_iam_role" "mon_not_chnl_edt" {
  name = "roles/monitoring.notificationChannelEditor"
}

data "google_iam_role" "lumen_gce_setmetadata" {
  name = "organizations/781036668248/roles/lumen_gce_setmetadata"
}
"""

def get_static_iam_group_grants_tf() -> str:
    return """resource "google_project_iam_member" "prj_admin_team" {
  project = var.project_id
  member  = "group:gcp.${var.project_id}.admin@lumen.com"

  for_each = tomap({
    (data.google_iam_role.sm_secret_version_mgr.title)  = data.google_iam_role.sm_secret_version_mgr.name,
    (data.google_iam_role.sm_secret_accessor.title)     = data.google_iam_role.sm_secret_accessor.name,
    (data.google_iam_role.techsupport_editor.title)     = data.google_iam_role.techsupport_editor.name,
    (data.google_iam_role.log_config_writer.title)      = data.google_iam_role.log_config_writer.name,
    (data.google_iam_role.log_viewer.title)             = data.google_iam_role.log_viewer.name,
    (data.google_iam_role.mon_alt_policy_edt.title)     = data.google_iam_role.mon_alt_policy_edt.name,
    (data.google_iam_role.mon_edt.title)                = data.google_iam_role.mon_edt.name,
    (data.google_iam_role.mon_not_chnl_edt.title)       = data.google_iam_role.mon_not_chnl_edt.name,
    (data.google_iam_role.viewer.title)                 = data.google_iam_role.viewer.name,
    (data.google_iam_role.compute_oslogin.title)        = data.google_iam_role.compute_oslogin.name,
    (data.google_iam_role.compute_viewer.title)         = data.google_iam_role.compute_viewer.name,
    (data.google_iam_role.lumen_gce_setmetadata.title)  = data.google_iam_role.lumen_gce_setmetadata.name,
    (data.google_iam_role.compute_admin.title)          = data.google_iam_role.compute_admin.name,
    (data.google_iam_role.svc_acct_token_creator.title) = data.google_iam_role.svc_acct_token_creator.name,
    (data.google_iam_role.svc_acct_user.title)          = data.google_iam_role.svc_acct_user.name

  })
  role = each.value
}

resource "google_project_iam_member" "prj_dev_team" {
  project = var.project_id
  member  = "group:gcp.${var.project_id}.dev-team@lumen.com"

  for_each = tomap({
    (data.google_iam_role.sm_secret_version_mgr.title) = data.google_iam_role.sm_secret_version_mgr.name,
    (data.google_iam_role.sm_secret_accessor.title)    = data.google_iam_role.sm_secret_accessor.name,
    (data.google_iam_role.techsupport_editor.title)    = data.google_iam_role.techsupport_editor.name,
    (data.google_iam_role.log_config_writer.title)     = data.google_iam_role.log_config_writer.name,
    (data.google_iam_role.log_viewer.title)            = data.google_iam_role.log_viewer.name,
    (data.google_iam_role.mon_alt_policy_edt.title)    = data.google_iam_role.mon_alt_policy_edt.name,
    (data.google_iam_role.mon_edt.title)               = data.google_iam_role.mon_edt.name,
    (data.google_iam_role.mon_not_chnl_edt.title)      = data.google_iam_role.mon_not_chnl_edt.name,
    (data.google_iam_role.viewer.title)                = data.google_iam_role.viewer.name,
    (data.google_iam_role.compute_oslogin.title)       = data.google_iam_role.compute_oslogin.name
    (data.google_iam_role.compute_viewer.title)        = data.google_iam_role.compute_viewer.name
    (data.google_iam_role.lumen_gce_setmetadata.title) = data.google_iam_role.lumen_gce_setmetadata.name
    (data.google_iam_role.compute_admin.title)         = data.google_iam_role.compute_admin.name
  })
  role = each.value
}

resource "google_project_iam_member" "prj_ops_team" {
  project = var.project_id
  member  = "group:gcp.${var.project_id}.ops-team@lumen.com"

  for_each = tomap({
    (data.google_iam_role.sm_secret_version_mgr.title) = data.google_iam_role.sm_secret_version_mgr.name,
    (data.google_iam_role.sm_secret_accessor.title)    = data.google_iam_role.sm_secret_accessor.name,
    (data.google_iam_role.techsupport_editor.title)    = data.google_iam_role.techsupport_editor.name,
    (data.google_iam_role.log_config_writer.title)     = data.google_iam_role.log_config_writer.name,
    (data.google_iam_role.log_viewer.title)            = data.google_iam_role.log_viewer.name,
    (data.google_iam_role.mon_alt_policy_edt.title)    = data.google_iam_role.mon_alt_policy_edt.name,
    (data.google_iam_role.mon_edt.title)               = data.google_iam_role.mon_edt.name,
    (data.google_iam_role.mon_not_chnl_edt.title)      = data.google_iam_role.mon_not_chnl_edt.name,
    (data.google_iam_role.viewer.title)                = data.google_iam_role.viewer.name,
    (data.google_iam_role.compute_admin.title)         = data.google_iam_role.compute_admin.name
  })
  role = each.value
}

resource "google_project_iam_member" "prj_viewer" {
  project = var.project_id
  member  = "group:gcp.${var.project_id}.viewer@lumen.com"

  for_each = tomap({
    (data.google_iam_role.viewer.title) = data.google_iam_role.viewer.name,
  })
  role = each.value
}

resource "google_project_iam_member" "m2vm_prod_admin" {
  project = var.project_id
  member  = "group:gcp.${var.project_id_m2vm}.admin@lumen.com"
  for_each = tomap({
    (data.google_iam_role.iam_admin.title)      = data.google_iam_role.iam_admin.name,
    (data.google_iam_role.compute_viewer.title) = data.google_iam_role.compute_viewer.name,
  })
  role = each.value
}"""

def get_static_iam_service_account_tf() -> str:
    return """resource "google_project_iam_member" "sa_gce" {
  depends_on = [google_service_account.sa-gce]
  project    = var.project_id
  for_each = tomap({
    (data.google_iam_role.compute_admin.title)      = data.google_iam_role.compute_admin.name,
    (data.google_iam_role.compute_net_user.title)   = data.google_iam_role.compute_net_user.name,
    (data.google_iam_role.sm_secret_accessor.title) = data.google_iam_role.sm_secret_accessor.name,
  })
  role   = each.value
  member = "serviceAccount:${google_service_account.sa-gce.email}"
}

resource "google_project_iam_member" "sa_m2vm_default" {
  project = var.project_id
  for_each = tomap({
    (data.google_iam_role.vmmigration_serviceAgent.title) = data.google_iam_role.vmmigration_serviceAgent.name,
    (data.google_iam_role.iam_serviceAccountUser.title)   = data.google_iam_role.iam_serviceAccountUser.name,

  })
  role   = each.value
  member = "serviceAccount:service-998889948446@gcp-sa-vmmigration.iam.gserviceaccount.com"
}"""

def get_static_service_accounts_tf() -> str:
    return """resource "google_service_account" "sa-gce" {
  project      = var.project_id
  account_id   = "sa-gce"
  display_name = "Service Account - for GCE"
  description  = "service account for terraform"
}

resource "google_service_account_iam_binding" "sa-gce-dev-acc-binding" {
  depends_on         = [google_service_account.sa-gce]
  service_account_id = google_service_account.sa-gce.name
  for_each = tomap({
    (data.google_iam_role.svc_acct_token_creator.title) = data.google_iam_role.svc_acct_token_creator.name,
    (data.google_iam_role.svc_acct_user.title)          = data.google_iam_role.svc_acct_user.name,
  })

  role = each.value
  members = [
    "group:gcp.${var.project_id}.dev-team@lumen.com",
    "group:gcp.${var.project_id}.ops-team@lumen.com",
  ]
}
"""
    
def get_static_iam_variables_tf() -> str:
    return """variable "project_id" {
  description = "GCP Project ID"
  type        = string
  validation {
    condition     = length(var.project_id) > 4
    error_message = "The project_id field must be longer than 4 characters"
  }
}

variable "project_id_m2vm" {
  description = "GCP Project ID"
  type        = string
  validation {
    condition     = length(var.project_id_m2vm) > 4
    error_message = "The project_id field must be longer than 4 characters"
  }
}"""

def get_static_budget_variables_tf() -> str:
    return """variable "project_id" {
  description = "The ID of the project"
  type        = string
}

variable "project_billing_id" {
  description = "Billing ID to attach project to"
  type        = string
  default     = ""
}

variable "project_budget_amount" {
  description = "Budget amount threshold"
  type        = string
  default     = "100"
}

variable "project_budget_email" {
  description = "Email for Budget exceed notifications"
  type        = string
  default     = ""
}
"""

def get_static_policies_variables_tf():
  return """
variable "project_id" {
  description = "Pick a Project ID"
  type        = string
}

variable "project_apply_vpc_service_control_policy" {
  type        = bool
  description = "apply service control policy"
  default     = true
}

variable "project_override_vpc_service_control_policy" {
  type        = string
  description = "Name of VPC Service Control Policy"
  default     = ""
}

variable "project_override_vpc_service_control_policy_use_dryrun" {
  type        = bool
  description = "Use VPC Service Dry Run Control Policy"
  default     = false
}

variable "project_deploy_cloudarmor_policy" {
  type        = bool
  description = "Apply cloud armor policy for project"
  default     = false
}

variable "project_use_lumen_net_infra_shared_vpc" {
  type        = bool
  description = "use old on prem connectivity with MPLS"
  default     = false
}

# variable "project_locations_restrict" {
#   description = "restrict regions for the project to deploy resources into"
#   type        = bool
#   default     = true
# }

variable "project_locations_allowed" {
  description = "allowed regions for the project to deploy resources into"
  type        = list(any)
  default     = ["us-central1", "us-east4"]
}

variable "use_gce" {
  description = "Does the project use GCE"
  type        = bool
  default     = true
}

variable "patch_deployment_day_of_week" {
  description = "day of week for patches"
  type        = string
  default     = "SATURDAY"
}

variable "patch_deployment_hour_of_day" {
  description = "day of week for patches"
  type        = number
  default     = 22
}

variable "patch_deployment_minute_of_day" {
  description = "day of week for patches"
  type        = number
  default     = 00
}

variable "patch_schedule_type" {
  description = "Frequency of patch deployment"
  type        = string
  default     = "monthly"
}

variable "patch_deployment_week_ordinal" {
  description = "Week number in a month. 1-4 indicates the 1st to 4th week of the month. -1 indicates the last week of the month"
  type        = number
  default     = 4
}
  """