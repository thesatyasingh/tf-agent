def generate_subnet_tf(app_acronym: str, env: str, cidr_range: str, cidr_size: str, module_version: str) -> str:
    """Generates the subnet .tf file content."""
    
    # Handle the specific prod vs np suffix rules you mentioned
    env_suffix = "prod" if env.lower() == "prod" else "np"
    
    return f"""locals {{
  prj-{app_acronym}-01-net-name = "gcp-prj-{app_acronym}"

  prj-{app_acronym}-01-use-acct-set = [
    "group:gcp.${{data.google_project.prj-{app_acronym}-01.project_id}}.admin@lumen.com",
    "serviceAccount:service-998889948446@gcp-sa-vmmigration.iam.gserviceaccount.com",
    "serviceAccount:sa-m2vm-admin@${{data.google_project.prj-m2vm-01.project_id}}.iam.gserviceaccount.com",
    "group:gcp.${{data.google_project.prj-m2vm-01.project_id}}.admin@lumen.com",
  ]

  prj-{app_acronym}-01-view-acct-set = [
    "group:gcp.${{data.google_project.prj-{app_acronym}-01.project_id}}.admin@lumen.com",
  ]
}}

data "google_project" "prj-{app_acronym}-01" {{
  project_id = "${{local.prj-{app_acronym}-01-net-name}}-{env_suffix}-01"
}}

module "prj-{app_acronym}-01-net" {{
  depends_on = [data.google_project.prj-{app_acronym}-01]

  source = "github.com/CenturyLink/tf-modules--gcp-tf-modules//net/shared_vpc?ref={module_version}"

  host_prj_id   = var.host_prj_id
  srvc_prj_id   = data.google_project.prj-{app_acronym}-01.project_id
  env           = var.env
  view_acct_set = local.prj-{app_acronym}-01-view-acct-set

  networks = [{{
    vpc  = "vpc-core-net-int-${{var.env}}-001",
    type = "prj",
    net_map = {{
      "net-gce-eus4" = {{
        name       = "gcp-net-gce-${{local.prj-{app_acronym}-01-net-name}}-${{var.env}}-eus4-01",
        region     = "us-east4"
        cidr       = "{cidr_range}"
        cidr_size  = "{cidr_size}",
        cidr_token = "GCE_NET",
        subnets    = {{}}
      }},
    }},
    use_acct_set          = local.prj-{app_acronym}-01-use-acct-set,
    svc_acct_gke          = null,
    svc_acct_dataproc     = null,
    private_google_access = true,
    purpose               = "PRIVATE"
  }}]
  additional_network_urls = []
}}
"""