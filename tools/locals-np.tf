locals {
  mag_magic_np_project_id = "gcp-prj-mag-magic-np-01"
  mag_magic_np_app_owners = ["rabih.nahas@lumen.com", "jeff.torchia@lumen.com", "sam.plankis@lumen.com", "jeanene.blake@lumen.com"]
}

module "gcp-prj-mag-magic-np-admin-team" {
  source       = "../modules/create_and_link"
  project_id   = local.mag_magic_np_project_id
  group_suffix = "admin"
  group_owners = concat(local.gcp_ccoe_owners, local.mag_magic_np_app_owners)
}

module "gcp-prj-mag-magic-np-dev-team" {
  source       = "../modules/create_and_link"
  project_id   = local.mag_magic_np_project_id
  group_suffix = "dev-team"
  group_owners = concat(local.gcp_ccoe_owners, local.mag_magic_np_app_owners)
}

module "gcp-prj-mag-magic-np-ops-team" {
  source       = "../modules/create_and_link"
  project_id   = local.mag_magic_np_project_id
  group_suffix = "ops-team"
  group_owners = concat(local.gcp_ccoe_owners, local.mag_magic_np_app_owners)
}

module "gcp-prj-mag-magic-np-viewer" {
  source       = "../modules/create_and_link"
  project_id   = local.mag_magic_np_project_id
  group_suffix = "viewer"
  group_owners = concat(local.gcp_ccoe_owners, local.mag_magic_np_app_owners)
}

