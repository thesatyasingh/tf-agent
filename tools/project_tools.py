import os
import sys
import json
import subprocess
import urllib.request
from datetime import datetime
from utils.system_utils import run_cmd, load_mappings
from templates.project_templates import *

def get_latest_module_version() -> str:
    """
    Fetches the latest tag from the GitHub repository that strictly matches 
    the semantic versioning format vM.N.O (e.g., v5.5.3, v12.0.1).
    """
    # Replace with your actual GitHub API URL or method if you use authentication
    url = "https://api.github.com/repos/CenturyLink/tf-modules--gcp-tf-modules/releases"
    
    try:
        req = urllib.request.Request(url)
        # If you need a token, add it here: req.add_header("Authorization", "Bearer YOUR_TOKEN")
        
        with urllib.request.urlopen(req) as response:
            tags_data = json.loads(response.read().decode())
            
        valid_versions = []
        # Regex to match exactly v followed by 1-2 digits . 1-2 digits . 1-2 digits
        pattern = re.compile(r"^v(\d{1,2})\.(\d{1,2})\.(\d{1,2})$")
        
        for tag_obj in tags_data:
            tag_name = tag_obj.get("name", "")
            match = pattern.match(tag_name)
            if match:
                # Convert version parts to integers for accurate mathematical sorting
                # (so v2.10.0 is evaluated as higher than v2.9.0)
                major, minor, patch = map(int, match.groups())
                valid_versions.append((major, minor, patch, tag_name))
                
        if not valid_versions:
            # Fallback version if no matching tags are found
            return "v5.5.3" 
            
        # Sort descending (highest version first) and grab the original tag string
        valid_versions.sort(reverse=True)
        return valid_versions[0][3]
        
    except Exception as e:
        print(f"Failed to fetch tags: {e}")
        # Fallback version in case of network or API rate limit issues
        return "v5.5.3"

def run_and_parse_tf_plan(tf_dir: str, tf_env: dict, module_name: str) -> tuple[str, bool]:
    """Helper to run init and plan, stream output, and intelligently parse the result."""
    # Run Init
    run_cmd("terraform init -no-color -input=false", cwd=tf_dir, env=tf_env)
    
    # Run Plan
    plan_cmd = "terraform plan -no-color -detailed-exitcode -input=false"
    print(f"\n[Executing in {module_name}]: {plan_cmd}")
    process = subprocess.Popen(
        plan_cmd, 
        shell=True, 
        cwd=tf_dir, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT, 
        text=True, 
        env=tf_env,
        bufsize=1
    )
    
    plan_lines = []
    for line in process.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        plan_lines.append(line)
        
    process.wait()
    plan_output = "".join(plan_lines).strip()
    plan_failed = process.returncode == 1
    
    # Parse exactly like app_onboarding.py
    relevant_start = -1
    markers = [
        "Terraform used the selected providers to generate the following execution plan.",
        "Terraform planned the following actions",
        "No changes. Your infrastructure matches the configuration."
    ]
    
    for marker in markers:
        idx = plan_output.find(marker)
        if idx != -1:
            if relevant_start == -1 or idx < relevant_start:
                relevant_start = idx
                
    if relevant_start == -1 and "Error:" in plan_output:
        relevant_start = plan_output.find("Error:")
        
    if relevant_start != -1:
        clean_plan_output = plan_output[relevant_start:].strip()
    else:
        clean_plan_output = plan_output 
        
    if len(clean_plan_output) > 60000:
         clean_plan_output = clean_plan_output[:60000] + "\n\n... [TRUNCATED DUE TO GITHUB LIMITS] ..."
         
    return clean_plan_output, plan_failed

def prepare_and_plan_project(app_acronym: str, environment: str, project_folder_id: str, budget_email: str, cms_vars: dict, jira_ticket: str) -> str:
    """
    Step 1: Clones Landing Zone repo, generates 4-module structure, and runs TF plans.
    """
    github_token = os.environ.get("GITHUB_PAT")
    if not github_token:
        return "Error: GITHUB_PAT environment variable is not set."
        
    gcp_sa = os.environ.get("GCP_IMPERSONATE_SA")
    github_org = "CenturyLink"
    repo_name = "tf-landingzones-infra--gcp-workloads-infra"
    
    try:
        # Load Mappings
        mappings = load_mappings()
        app_data = mappings.get(app_acronym.upper()) 
        if not app_data:
            return f"Error: Application acronym {app_acronym} not found in mappings.json."
            
        # Normalize naming conventions
        acronym = app_data['acronym'].lower()
        domain = app_data['domain'].lower()
        
        long_env = "prod" if environment.lower() == "prod" else "nonprod"
        short_env = "prod" if environment.lower() == "prod" else "np"
        
        svc_domain = f"svc-{long_env}-{domain}"
        project_id = f"gcp-prj-{acronym}-{short_env}-01"
        
        # Calculate tags and branches
        latest_version = get_latest_module_version()
        clean_version = latest_version.lstrip("v").replace(".", "_")
        date_str = datetime.now().strftime("%y%m%d")
        tags_tmplver = f"{clean_version}__{date_str}"
        
        branch_name = f"branch/{date_str}-{jira_ticket}-{acronym}-{long_env}-landingzone-project"
        repo_url = f"https://{github_token}@github.com/{github_org}/{repo_name}.git"
        
        timestamp = datetime.now().strftime("%H%M%S_%y%m%d")
        run_clone_dir = os.path.join("repo-clone", timestamp)
        os.makedirs(run_clone_dir, exist_ok=True)
        full_repo_path = os.path.join(run_clone_dir, repo_name)
        
        # Clone and Branch (HTTPS auth injection)
        run_cmd(f"git clone {repo_url}", cwd=run_clone_dir)
        run_cmd("git checkout main", cwd=full_repo_path)
        run_cmd("git pull origin main", cwd=full_repo_path)
        run_cmd(f"git checkout -b {branch_name}", cwd=full_repo_path)
        
        # Isolated Git Config
        isolated_gitconfig = os.path.abspath(os.path.join(run_clone_dir, ".isolated_gitconfig"))
        git_config_content = f"""[url "https://{github_token}@github.com/"]
\tinsteadOf = https://github.com/
[credential]
\thelper =
"""
        with open(isolated_gitconfig, 'w') as f:
            f.write(git_config_content)
            
        # Construct Path: root/[env]/svc-[env]-[domain]/[env]-[app]/gcp-prj-[app]-[env]-01/
        project_dir = os.path.join(full_repo_path, "root", long_env, svc_domain, f"{long_env}-{acronym}", project_id)
        modules = ["project", "project-budget", "project-policies", "iam"]
        
        for mod in modules:
            os.makedirs(os.path.join(project_dir, mod), exist_ok=True)

        # Generate & Write Files
        for mod in modules:
            mod_path = os.path.join(project_dir, mod)
            
            with open(os.path.join(mod_path, "provider.tf"), "w") as f:
                f.write(generate_provider_tf(long_env, domain, acronym, short_env, mod))
            with open(os.path.join(mod_path, "terragrunt.hcl"), "w") as f:
                f.write(generate_terragrunt_hcl())
                
            if mod == "project":
                tfvars = generate_project_tfvars(acronym, short_env, project_folder_id, cms_vars, tags_tmplver)
                with open(os.path.join(mod_path, "main.tf"), "w") as f:
                    f.write(get_static_project_main_tf(latest_version))
                with open(os.path.join(mod_path, "variables.tf"), "w") as f:
                    f.write(get_static_project_variables_tf())
                    
            elif mod == "project-budget":
                tfvars = generate_budget_tfvars(acronym, short_env, budget_email)
                with open(os.path.join(mod_path, "main.tf"), "w") as f:
                    f.write(get_static_budget_main_tf(latest_version))
                with open(os.path.join(mod_path, "variables.tf"), "w") as f:
                    f.write(get_static_budget_variables_tf())
                    
            elif mod == "project-policies":
                tfvars = generate_policies_tfvars(acronym, short_env)
                with open(os.path.join(mod_path, "main.tf"), "w") as f:
                    f.write(get_static_policies_main_tf(latest_version))
                with open(os.path.join(mod_path, "variables.tf"), "w") as f:
                    f.write(get_static_policies_variables_tf())
                    
            elif mod == "iam":
                tfvars = generate_iam_tfvars(acronym, short_env)
                with open(os.path.join(mod_path, "data.tf"), "w") as f:
                    f.write(get_static_iam_data_tf())
                with open(os.path.join(mod_path, "iam-group-grants.tf"), "w") as f:
                    f.write(get_static_iam_group_grants_tf())
                with open(os.path.join(mod_path, "iam-service-account.tf"), "w") as f:
                    f.write(get_static_iam_service_account_tf())
                with open(os.path.join(mod_path, "service-accounts.tf"), "w") as f:
                    f.write(get_static_service_accounts_tf())
                with open(os.path.join(mod_path, "variables.tf"), "w") as f:
                    f.write(get_static_iam_variables_tf())
                
            with open(os.path.join(mod_path, "terraform.tfvars"), "w") as f:
                f.write(tfvars)

        # Environment setup for Terraform execution
        tf_env = os.environ.copy()
        if gcp_sa:
            tf_env["GOOGLE_IMPERSONATE_SERVICE_ACCOUNT"] = gcp_sa
        tf_env["GIT_CONFIG_GLOBAL"] = isolated_gitconfig
        
        pr_markdown = ""
        any_plan_failed = False
        
        # Run plans for all 4 modules sequentially
        for mod in modules:
            mod_path = os.path.join(project_dir, mod)
            clean_plan, failed = run_and_parse_tf_plan(mod_path, tf_env, mod)
            
            if failed:
                any_plan_failed = True
                
            pr_markdown += (
                f"<summary> {mod} plan output </summary>\n"
                f"<details>\n"
                f"{clean_plan}\n"
                f"</details>\n\n"
            )

        # Save the combined PR Body outside the repo
        pr_body_path = os.path.join(run_clone_dir, ".lz_pr_body.md")
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

def submit_project_pr(workspace_path: str, branch_name: str, jira_ticket: str, app_acronym: str, env_short: str) -> str:
    """
    Step 2: Commits and pushes the Landing Zone branch using the aggregated manual PR workflow.
    """
    try:
        print("\n" + "="*50)
        print(f"🚀 PUSHING BRANCH FOR {app_acronym.upper()} (LANDING ZONE)")
        print("="*50)
        
        run_clone_dir = os.path.dirname(workspace_path)
        pr_body_path = os.path.join(run_clone_dir, ".lz_pr_body.md")
        
        with open(pr_body_path, "r") as f:
            pr_body = f.read()
            
        commit_msg_path = os.path.abspath(os.path.join(run_clone_dir, ".git_commit_msg.txt"))
        commit_title = f"{jira_ticket}: {app_acronym.upper()} {env_short} project creation"
        
        with open(commit_msg_path, "w") as f:
            f.write(f"{commit_title}\n\n{pr_body}")
        
        run_cmd("git add .", cwd=workspace_path)
        run_cmd(f'git commit -F "{commit_msg_path}"', cwd=workspace_path)
        run_cmd(f"git push origin {branch_name}", cwd=workspace_path)
        
        print(f"✅ Branch successfully pushed: {branch_name}\n")
        
        return f"Success! Branch `{branch_name}` pushed. The user can navigate to GitHub to open the PR with all 4 plans auto-filled."
        
    except Exception as e:
        print(f"\n❌ Error during git push: {str(e)}")
        return f"Push failed: {str(e)}"