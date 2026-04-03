import os
import json
from datetime import datetime
from utils.system_utils import run_cmd, load_mappings
from templates.gce_templates import *
from tools.network_tools import get_latest_module_version, run_and_parse_tf_plan

def prepare_and_plan_gce(app_acronym: str, environment: str, jira_ticket: str, vm_configs_json: str) -> str:
    """
    Clones Workloads LZ repo, increments GCE folder indexes, creates TF files, and plans.
    """
    github_token = os.environ.get("GITHUB_PAT")
    gcp_sa = os.environ.get("GCP_IMPERSONATE_SA")
    github_org = "CenturyLink"
    repo_name = "tf-landingzones-infra--gcp-workloads-infra"
    
    try:
        vm_configs = json.loads(vm_configs_json)
        mappings = load_mappings()
        app_data = mappings.get(app_acronym.upper()) 
        if not app_data:
            return f"Error: Application acronym {app_acronym} not found in mappings.json."
            
        acronym = app_data['acronym'].lower()
        domain = app_data['domain'].lower()
        sysgen = app_data['sysgen']
        
        long_env = "prod" if environment.lower() == "prod" else "nonprod"
        short_env = "prod" if environment.lower() == "prod" else "np"
        
        # --- THE FIX: Specific environment mapping for the Shared VPC ---
        host_env = "prd" if environment.lower() == "prod" else "np"
        
        svc_domain = f"svc-{long_env}-{domain}"
        project_id = f"gcp-prj-{acronym}-{short_env}-01"
        host_project_id = f"prj-lmn-core-nw-{host_env}-01" 
        sa_email = f"sa-gce@{project_id}.iam.gserviceaccount.com"
        subnetwork = f"gcp-net-gce-gcp-prj-{acronym}-{long_env}-eus4-01"
        
        latest_version = get_latest_module_version()
        date_str = datetime.now().strftime("%y%m%d")
        branch_name = f"branch/{date_str}-{jira_ticket}-{acronym}-{long_env}-gce-provisioning"
        repo_url = f"https://{github_token}@github.com/{github_org}/{repo_name}.git"
        
        # Workspace setup
        timestamp = datetime.now().strftime("%H%M%S_%y%m%d")
        run_clone_dir = os.path.join("repo-clone", timestamp)
        os.makedirs(run_clone_dir, exist_ok=True)
        full_repo_path = os.path.join(run_clone_dir, repo_name)
        
        run_cmd(f"git clone {repo_url}", cwd=run_clone_dir)
        run_cmd("git checkout main", cwd=full_repo_path)
        run_cmd("git pull origin main", cwd=full_repo_path)
        run_cmd(f"git checkout -b {branch_name}", cwd=full_repo_path)
        
        isolated_gitconfig = os.path.abspath(os.path.join(run_clone_dir, ".isolated_gitconfig"))
        with open(isolated_gitconfig, 'w') as f:
            f.write(f"""[url "https://{github_token}@github.com/"]\n\tinsteadOf = https://github.com/\n[credential]\n\thelper =\n""")
            
        tf_env = os.environ.copy()
        if gcp_sa: tf_env["GOOGLE_IMPERSONATE_SERVICE_ACCOUNT"] = gcp_sa
        tf_env["GIT_CONFIG_GLOBAL"] = isolated_gitconfig

        # Target directory logic
        gce_base_dir = os.path.join(full_repo_path, "root", long_env, svc_domain, f"{long_env}-{acronym}", project_id, "gce")
        os.makedirs(gce_base_dir, exist_ok=True)
        
        # Pre-scan for existing indexes
        existing_folders = [d for d in os.listdir(gce_base_dir) if os.path.isdir(os.path.join(gce_base_dir, d)) and d.startswith(f"gce-{acronym}-{short_env}-use4-")]
        current_max_index = 0
        for f in existing_folders:
            try:
                idx = int(f.split("-")[-1])
                current_max_index = max(current_max_index, idx)
            except ValueError:
                pass
                
        pr_markdown = ""
        any_plan_failed = False
        
        # Iterate over all requested VMs
        for config in vm_configs:
            current_max_index += 1
            idx_str = f"{current_max_index:02d}" 
            
            # Short code folder vs Long code backend
            folder_name = f"gce-{acronym}-{short_env}-use4-{idx_str}"
            gcs_prefix_name = f"gce-{acronym}-{long_env}-us-east4-{idx_str}"
            
            vm_dir = os.path.join(gce_base_dir, folder_name)
            os.makedirs(vm_dir, exist_ok=True)
            
            gcs_full_prefix = f"root-lz/{long_env}/{svc_domain}/{long_env}-{acronym}/{project_id}/gce/{gcs_prefix_name}"
            full_image_path = f"https://www.googleapis.com/compute/v1/{config['image_path']}"
            
            # Write standard files
            with open(os.path.join(vm_dir, "main.tf"), "w") as f: f.write(generate_gce_main_tf(latest_version))
            with open(os.path.join(vm_dir, "provider.tf"), "w") as f: f.write(generate_gce_provider_tf(gcs_full_prefix))
            with open(os.path.join(vm_dir, "variables.tf"), "w") as f: f.write(generate_gce_variables_tf())
            with open(os.path.join(vm_dir, "terragrunt.hcl"), "w") as f: f.write(generate_gce_terragrunt_hcl())
            with open(os.path.join(vm_dir, "terraform.tfvars"), "w") as f: 
                f.write(generate_gce_tfvars(
                    project_id, host_project_id, config["instance_name"], long_env, config["disk_type"],
                    config["type"], subnetwork, full_image_path, sa_email, config["size"], sysgen, config["zone"]
                ))
            
            # Handle Optional Additional Disks
            additional_disks = config.get("additional_disks", [])
            for i, disk_size in enumerate(additional_disks, start=1):
                disk_suffix = f"{i:02d}"
                disk_tf = generate_attached_disk_tf(acronym, disk_suffix, disk_size, config["instance_name"])
                with open(os.path.join(vm_dir, f"gce_attached_disk_{acronym}_{disk_suffix}.tf"), "w") as f:
                    f.write(disk_tf)

            # Plan for this specific VM folder
            clean_plan, failed = run_and_parse_tf_plan(vm_dir, tf_env, folder_name)
            if failed: any_plan_failed = True
            
            pr_markdown += f"<summary> GCE Plan Output ({folder_name}) </summary>\n<details>\n{clean_plan}\n</details>\n\n"

        pr_body_path = os.path.join(run_clone_dir, ".gce_pr_body.md")
        with open(pr_body_path, "w") as f:
            f.write(pr_markdown.strip())

        return json.dumps({
            "status": "success",
            "plan_failed": any_plan_failed,
            "workspace_path": full_repo_path,
            "branch_name": branch_name,
            "app_acronym": acronym,
            "env_short": short_env,
            "jira_ticket": jira_ticket
        })
        
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def submit_gce_pr(workspace_path: str, branch_name: str, jira_ticket: str, app_acronym: str, env_short: str) -> str:
    try:
        run_clone_dir = os.path.dirname(workspace_path)
        with open(os.path.join(run_clone_dir, ".gce_pr_body.md"), "r") as f: pr_body = f.read()
            
        commit_msg_path = os.path.abspath(os.path.join(run_clone_dir, ".git_commit_msg.txt"))
        with open(commit_msg_path, "w") as f: f.write(f"{jira_ticket}: {app_acronym.upper()} {env_short} GCE instance creation\n\n{pr_body}")
        
        run_cmd("git add .", cwd=workspace_path)
        run_cmd(f'git commit -F "{commit_msg_path}"', cwd=workspace_path)
        run_cmd(f"git push origin {branch_name}", cwd=workspace_path)
        return f"Success! Branch `{branch_name}` pushed to GitHub."
    except Exception as e:
        return f"Push failed: {str(e)}"