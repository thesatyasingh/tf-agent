locals {
  netengine_prod_project_id = "gcp-prj-netengine-prod-01"
  netengine_prod_app_owners = ["rabih.nahas@lumen.com", "jeff.torchia@lumen.com", "sam.plankis@lumen.com", "jeanene.blake@lumen.com"]
}

module "gcp-prj-netengine-prod-01-admin-team" {
  source       = "../modules/create_and_link"
  project_id   = local.netengine_prod_project_id
  group_suffix = "admin"
  group_owners = concat(local.gcp_ccoe_owners, local.netengine_prod_app_owners)
}

module "gcp-prj-netengine-prod-01-dev-team" {
  source       = "../modules/create_and_link"
  project_id   = local.netengine_prod_project_id
  group_suffix = "dev-team"
  group_owners = concat(local.gcp_ccoe_owners, local.netengine_prod_app_owners)
}

module "gcp-prj-netengine-prod-01-ops-team" {
  source       = "../modules/create_and_link"
  project_id   = local.netengine_prod_project_id
  group_suffix = "ops-team"
  group_owners = concat(local.gcp_ccoe_owners, local.netengine_prod_app_owners)
}

module "gcp-prj-netengine-prod-01-viewer" {
  source       = "../modules/create_and_link"
  project_id   = local.netengine_prod_project_id
  group_suffix = "viewer"
  group_owners = concat(local.gcp_ccoe_owners, local.netengine_prod_app_owners)
}
