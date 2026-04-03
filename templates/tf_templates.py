def generate_adgroup_tf(app_acronym: str, env_short: str, project_id: str, owners: list[str]) -> str:
    """Generates the Terraform content for the AD Groups adhering to the team standard."""
    
    # 1. Create the locals prefix (e.g., mag_magic_prod)
    local_prefix = f"{app_acronym.lower().replace('-', '_')}_{env_short}"
    
    formatted_owners = ", ".join([f'"{owner}"' for owner in owners])
    
    tf_content = f"""locals {{
  {local_prefix}_project_id = "{project_id}"
  {local_prefix}_app_owners = [{formatted_owners}]
}}

"""
    # 2. Base module name strips the -01 (e.g., gcp-prj-mag-magic-prod)
    base_module_name = f"gcp-prj-{app_acronym.lower()}-{env_short}"
    
    # Define groups with their module name suffixes and their actual variable suffixes
    groups = [
        {"module_suffix": "admin-team", "group_suffix": "admin"},
        {"module_suffix": "dev-team", "group_suffix": "dev-team"},
        {"module_suffix": "ops-team", "group_suffix": "ops-team"},
        {"module_suffix": "viewer", "group_suffix": "viewer"}
    ]
    
    for group in groups:
        tf_content += f"""module "{base_module_name}-{group['module_suffix']}" {{
  source       = "../modules/create_and_link"
  project_id   = local.{local_prefix}_project_id
  group_suffix = "{group['group_suffix']}"
  group_owners = concat(local.gcp_ccoe_owners, local.{local_prefix}_app_owners)
}}

"""
    return tf_content

def generate_folder_tf(app_acronym: str, env_short: str) -> str:
    """Generates the Terraform content for the folder module."""
    
    prefix = "prod" if env_short == "prod" else "nonprod"
    module_name = f"{prefix}-{app_acronym.lower()}"
    
    # Adding \n\n at the very start ensures a clean visual break 
    # even if the previous block lacked an EOF newline.
    tf_content = f"""module "{module_name}" {{
  source             = "../../../"
  parent_folder_name = var.parent_folder_name
  folder_name        = "{module_name}"
}}
"""
    return tf_content