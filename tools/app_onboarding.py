import os
import sys
import json
import subprocess
from datetime import datetime
from utils.system_utils import run_cmd, load_mappings
from utils.github_utils import create_pull_request
from templates.tf_templates import generate_adgroup_tf, generate_folder_tf

def prepare_and_plan_terraform(app_acronym: str, environment: str, owners: list[str], jira_ticket: str) -> str:
    """
    Step 1: Clones repo, writes TF files, runs TF plan. Returns workspace data.
    """
    github_token = os.environ.get("GITHUB_PAT")
    if not github_token:
        return "Error: GITHUB_PAT environment variable is not set."
        
    gcp_sa = os.environ.get("GCP_IMPERSONATE_SA")
    github_org = "CenturyLink"
        
    try:
        mappings = load_mappings()
        app_data = mappings.get(app_acronym.upper()) 
        if not app_data:
            return f"Error: Application acronym {app_acronym} not found in mappings.json."
            
        acronym = app_data['acronym'].lower()
        domain_suffix = app_data['domain'].replace('-', '_')
        env_short = "prod" if environment.lower() == "prod" else "np"
        domain_folder = f"svc_{env_short}_{domain_suffix}"
        env_folder_prefix = "prod" if environment.lower() == "prod" else "nonprod"
        project_id = f"gcp-prj-{acronym}-{env_short}-01"
        
        branch_date_str = datetime.now().strftime("%y%m%d")
        branch_name = f"branch/{branch_date_str}-{jira_ticket}-{acronym}-{env_short}-adgroup-folder-creation"
        
        repo_name = "tf-core-it-infra--gcp-coreit-infra"
        repo_url = f"https://{github_token}@github.com/{github_org}/{repo_name}.git"
        
        timestamp = datetime.now().strftime("%H%M%S_%y%m%d")
        run_clone_dir = os.path.join("repo-clone", timestamp)
        os.makedirs(run_clone_dir, exist_ok=True)
        full_repo_path = os.path.join(run_clone_dir, repo_name)
        
        # Clone and branch
        run_cmd(f"git clone {repo_url}", cwd=run_clone_dir)
        run_cmd("git checkout main", cwd=full_repo_path)
        run_cmd("git pull origin main", cwd=full_repo_path)
        run_cmd(f"git checkout -b {branch_name}", cwd=full_repo_path)
        
        # Write Files
        adgroup_file_path = os.path.join(full_repo_path, "azure-groups", "core-shared", f"{project_id}.tf")
        with open(adgroup_file_path, 'w') as f:
            f.write(generate_adgroup_tf(acronym, env_short, project_id, owners))
            
        main_tf_path = os.path.join(full_repo_path, "cloud", "lumen-org", "modules", "folders", "root_lz_projects", env_folder_prefix, domain_folder, "main.tf")
        
        # FIX: Intelligently check the end of the file to prevent duplicate blank lines
        prefix_newlines = ""
        if os.path.exists(main_tf_path):
            with open(main_tf_path, 'r') as f:
                content = f.read()
                if content:
                    # If it already has a blank line, add nothing.
                    if content.endswith('\n\n'):
                        prefix_newlines = ""
                    # If it ends right after the last bracket but has a return, add one newline.
                    elif content.endswith('\n'):
                        prefix_newlines = "\n"
                    # If it ends exactly on the bracket with no return at all, add two.
                    else:
                        prefix_newlines = "\n\n"
                        
        with open(main_tf_path, 'a') as f:
            f.write(prefix_newlines + generate_folder_tf(acronym, env_short))
        
        # --- NEW CHANGELOG LOGIC ---
        changelog_path = os.path.join(full_repo_path, "cloud", "lumen-org", "CHANGELOG.md")
        changelog_date = datetime.now().strftime("%y%m%d")
        
        # Match the capitalization in your example (prod vs Nonprod)
        env_display = "prod" if environment.lower() == "prod" else "Nonprod"
        
        # Format the entry exactly to your specifications
        changelog_entry = f"* [{jira_ticket}](https://lumen.atlassian.net/browse/{jira_ticket}) - {changelog_date}\n    * {app_acronym} {env_display} folder creation\n"

        if os.path.exists(changelog_path):
            with open(changelog_path, 'r') as f:
                changelog_lines = f.readlines()

            # Find the header and inject the new entry immediately below it
            for i, line in enumerate(changelog_lines):
                if "## Tickets" in line:
                    changelog_lines.insert(i + 1, changelog_entry)
                    break

            with open(changelog_path, 'w') as f:
                f.writelines(changelog_lines)
        else:
            print(f"\n[Warning]: CHANGELOG.md not found at {changelog_path}")
            
        # FIX: Create an isolated Git config file to force token auth for all sub-modules
        isolated_gitconfig = os.path.abspath(os.path.join(run_clone_dir, ".isolated_gitconfig"))
        git_config_content = f"""[url "https://{github_token}@github.com/"]
\tinsteadOf = https://github.com/
[credential]
\thelper =
"""
        with open(isolated_gitconfig, 'w') as f:
            f.write(git_config_content)
            
        # Run Terraform Plan
        tf_dir = os.path.join(full_repo_path, "cloud", "lumen-org")
        
        tf_env = os.environ.copy()
        if gcp_sa:
            tf_env["GOOGLE_IMPERSONATE_SERVICE_ACCOUNT"] = gcp_sa
            
        # Force Terraform's Git processes to use our isolated config
        tf_env["GIT_CONFIG_GLOBAL"] = isolated_gitconfig
            
        # FIX 1: Added -input=false to prevent invisible hangs
        init_output = run_cmd("terraform init -no-color -input=false", cwd=tf_dir, env=tf_env)
        
        plan_cmd = "terraform plan -no-color -detailed-exitcode -input=false"
        print(f"\n[Executing]: {plan_cmd}")
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
        
        # --- NEW PARSING LOGIC ---
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

        pr_body = f"""
<summary> Folder TF Plan </summary>
<details>
{clean_plan_output}
</details>
                    """
        # FIX: Save the PR body outside the repo so 'git add .' ignores it
        pr_body_path = os.path.join(run_clone_dir, ".pr_body.md")
        with open(pr_body_path, "w") as f:
            f.write(pr_body)

        return json.dumps({
            "status": "success",
            "plan_failed": plan_failed,
            "workspace_path": full_repo_path,
            "branch_name": branch_name,
            "app_acronym": app_acronym,
            "env_short": env_short,
            "jira_ticket": jira_ticket
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def submit_terraform_pr(workspace_path: str, branch_name: str, jira_ticket: str, app_acronym: str, env_short: str) -> str:
    """
    Step 2: Commits and pushes the branch, formatting the commit so GitHub auto-fills the manual PR.
    """
    try:
        print("\n" + "="*50)
        print(f"🚀 PUSHING BRANCH FOR {app_acronym} (MANUAL PR WORKFLOW)")
        print("="*50)
        
        # Read the PR body from the parent directory
        run_clone_dir = os.path.dirname(workspace_path)
        pr_body_path = os.path.join(run_clone_dir, ".pr_body.md")
        with open(pr_body_path, "r") as f:
            pr_body = f.read()
            
        # FIX 1: Wrap the path in os.path.abspath() to get the full hard drive path
        commit_msg_path = os.path.abspath(os.path.join(run_clone_dir, ".git_commit_msg.txt"))
        commit_title = f"{jira_ticket}: ADgroup/folder structures for {app_acronym} {env_short}"
        
        with open(commit_msg_path, "w") as f:
            f.write(f"{commit_title}\n\n{pr_body}")
        
        # Execute the Git commands
        run_cmd("git add .", cwd=workspace_path)
        
        # FIX 2: Wrap the path variable in double quotes so bash doesn't choke on spaces
        run_cmd(f'git commit -F "{commit_msg_path}"', cwd=workspace_path)
        run_cmd(f"git push origin {branch_name}", cwd=workspace_path)
        
        print(f"✅ Branch successfully pushed: {branch_name}\n")
        
        # Return a clean success message to the LLM agent
        return f"Success! Branch `{branch_name}` has been pushed. The user can now navigate to GitHub to manually open the PR."
        
    except Exception as e:
        print(f"\n❌ Error during git push: {str(e)}")
        return f"Push failed: {str(e)}"