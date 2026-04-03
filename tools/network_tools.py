import os
import sys
import json
import subprocess
import urllib.request
import re
import ipaddress
from datetime import datetime
from utils.system_utils import run_cmd
from templates.network_templates import generate_subnet_tf

def get_latest_module_version() -> str:
    """
    Fetches the latest tag from the GitHub repository that strictly matches 
    the semantic versioning format vM.N.O.
    """
    url = "https://api.github.com/repos/CenturyLink/tf-modules--gcp-tf-modules/tags"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            tags_data = json.loads(response.read().decode())
            
        valid_versions = []
        pattern = re.compile(r"^v(\d{1,2})\.(\d{1,2})\.(\d{1,2})$")
        
        for tag_obj in tags_data:
            tag_name = tag_obj.get("name", "")
            match = pattern.match(tag_name)
            if match:
                major, minor, patch = map(int, match.groups())
                valid_versions.append((major, minor, patch, tag_name))
                
        if not valid_versions:
            return "v5.5.3" 
            
        valid_versions.sort(reverse=True)
        return valid_versions[0][3]
        
    except Exception as e:
        print(f"Failed to fetch tags: {e}")
        return "v5.5.3"

def run_and_parse_tf_plan(tf_dir: str, tf_env: dict, module_name: str) -> tuple[str, bool]:
    """Helper to run init and plan, stream output, and intelligently parse the result."""
    run_cmd("terraform init -no-color -input=false", cwd=tf_dir, env=tf_env)
    
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

    # --- AGGRESSIVE NOISE FILTERING FOR SHARED VPC ---
    filtered_lines = []
    for line in plan_output.split('\n'):
        if any(noise in line for noise in [": Reading...", ": Read complete after", ": Refreshing state..."]):
            continue
        filtered_lines.append(line)
    plan_output = "\n".join(filtered_lines)
    # -------------------------------------------------
    
    # --- STRICT PARSING FOR PR BODY ---
    target_phrase = "Terraform will perform the following actions:"
    idx = plan_output.find(target_phrase)
    
    if idx != -1:
        clean_plan_output = plan_output[idx:].strip()
    elif "No changes." in plan_output:
        clean_plan_output = "No changes. Your infrastructure matches the configuration."
    elif "Error:" in plan_output:
        err_idx = plan_output.find("Error:")
        clean_plan_output = plan_output[err_idx:].strip()
    else:
        clean_plan_output = plan_output 
        
    if len(clean_plan_output) > 60000:
         clean_plan_output = clean_plan_output[:60000] + "\n\n... [TRUNCATED DUE TO GITHUB LIMITS] ..."
         
    return clean_plan_output, plan_failed

def prepare_and_plan_network(app_acronym: str, environment: str, cidr_range: str, jira_ticket: str) -> str:
    """
    Step 1: Clones Core IT Infra repo, generates subnet file, updates markdown logs, and runs TF plan.
    """
    github_token = os.environ.get("GITHUB_PAT")
    if not github_token:
        return "Error: GITHUB_PAT environment variable is not set."
        
    gcp_sa = os.environ.get("GCP_IMPERSONATE_SA")
    github_org = "CenturyLink"
    repo_name = "tf-core-it-infra--gcp-coreit-infra"
    
    try:
        app_acronym = app_acronym.lower()
        cidr_size = cidr_range.split('/')[-1]
        latest_version = get_latest_module_version()
        
        if environment.lower() == 'prod':
            folder_env = "prd"
            file_env = "prod"
            long_env = "production"
        else:
            folder_env = "np"
            file_env = "np"
            long_env = "nonproduction"
            
        date_str = datetime.now().strftime("%y%m%d")
        branch_name = f"branch/{date_str}-{jira_ticket}-{app_acronym}-{file_env}-subnet"
        repo_url = f"https://{github_token}@github.com/{github_org}/{repo_name}.git"
        
        # Setup isolated workspace
        timestamp = datetime.now().strftime("%H%M%S_%y%m%d")
        run_clone_dir = os.path.join("repo-clone", timestamp)
        os.makedirs(run_clone_dir, exist_ok=True)
        full_repo_path = os.path.join(run_clone_dir, repo_name)
        
        run_cmd(f"git clone {repo_url}", cwd=run_clone_dir)
        run_cmd("git checkout main", cwd=full_repo_path)
        run_cmd("git pull origin main", cwd=full_repo_path)
        run_cmd(f"git checkout -b {branch_name}", cwd=full_repo_path)
        
        isolated_gitconfig = os.path.abspath(os.path.join(run_clone_dir, ".isolated_gitconfig"))
        git_config_content = f"""[url "https://{github_token}@github.com/"]\n\tinsteadOf = https://github.com/\n[credential]\n\thelper =\n"""
        with open(isolated_gitconfig, 'w') as f:
            f.write(git_config_content)
            
        # -------------------------------------------------------------
        # 1. GENERATE SUBNET .TF FILE
        # -------------------------------------------------------------
        target_dir = os.path.join(full_repo_path, "root-lz", "core-shared", "network", f"prj-lmn-core-nw-{folder_env}-01", "project", "modules", "networks")
        os.makedirs(target_dir, exist_ok=True)
        plan_dir = os.path.join(full_repo_path, "root-lz", "core-shared", "network", f"prj-lmn-core-nw-{folder_env}-01", "project")
        
        filename = f"gcp-prj-{app_acronym}-{file_env}-01.tf"
        file_path = os.path.join(target_dir, filename)

        tf_content = generate_subnet_tf(app_acronym, environment, cidr_range, cidr_size, latest_version)
        with open(file_path, "w") as f:
            f.write(tf_content)

        # -------------------------------------------------------------
        # 2. UPDATE CHANGELOG.MD
        # -------------------------------------------------------------
        cl_dir_1 = os.path.join(full_repo_path, "root-lz", "core-shared", "network", f"prj-lmn-core-nw-{folder_env}-01", "project", "CHANGELOG.md")
        cl_dir_2 = os.path.join(full_repo_path, "root-lz", "core-shared", "network", f"prj-lmn-core-nw-{folder_env}-01", "CHANGELOG.md")
        changelog_path = cl_dir_1 if os.path.exists(cl_dir_1) else cl_dir_2

        if os.path.exists(changelog_path):
            with open(changelog_path, "r") as f:
                cl_lines = f.readlines()
            
            new_cl_entry = f"* [{jira_ticket}](https://lumen.atlassian.net/browse/{jira_ticket}) - {date_str}\n  * Adding subnet for {app_acronym.upper()} {file_env}\n"
            
            inserted = False
            for i, line in enumerate(cl_lines):
                if line.strip().lstrip('#').strip().lower() == "tickets":
                    insert_idx = i + 1
                    if insert_idx < len(cl_lines) and len(cl_lines[insert_idx].strip()) > 1 and set(cl_lines[insert_idx].strip()).issubset({'-', '='}):
                        insert_idx += 1
                        
                    cl_lines.insert(insert_idx, new_cl_entry)
                    inserted = True
                    break
                    
            if not inserted:
                cl_lines.insert(0, f"## Tickets\n{new_cl_entry}\n")
                
            with open(changelog_path, "w") as f:
                f.writelines(cl_lines)
        else:
            print(f"\n[WARNING] Could not find CHANGELOG.md in expected paths. Skipping changelog update.")

        # -------------------------------------------------------------
        # 3. UPDATE IPADDR MARKDOWN (CIDR Math & Auto-Alignment)
        # -------------------------------------------------------------
        ipaddr_path = os.path.join(full_repo_path, "root-lz", "core-shared", "network", f"IPADDR-{long_env}.md")
        if os.path.exists(ipaddr_path):
            with open(ipaddr_path, "r") as f:
                ip_lines = f.readlines()
                
            try:
                current_net = ipaddress.IPv4Network(cidr_range, strict=False)
                prev_net_int = int(current_net.network_address) - current_net.num_addresses
                predecessor_cidr = str(ipaddress.IPv4Network((prev_net_int, current_net.prefixlen)))
                user_ip_base = ".".join(str(current_net.network_address).split(".")[:3]) + "."
            except Exception:
                predecessor_cidr = "INVALID_CIDR_PARSE"
                user_ip_base = ""

            insert_idx = -1
            
            # Find the predecessor line
            for i, line in enumerate(ip_lines):
                if predecessor_cidr in line:
                    insert_idx = i + 1
                    break
            
            # Fallback if predecessor doesn't exist
            if insert_idx == -1 and user_ip_base:
                for i, line in enumerate(ip_lines):
                    if user_ip_base in line and line.strip().startswith("|"):
                        for j in range(i, len(ip_lines)):
                            if not ip_lines[j].strip().startswith("|"):
                                insert_idx = j
                                break
                        if insert_idx == -1:
                            insert_idx = len(ip_lines)
                        break

            # Dynamic Alignment formatting
            new_values = [
                f" {cidr_range} ",
                " us-east4 ",
                f" gcp-prj-{app_acronym}-{file_env}-01 ",
                " GCE_NET "
            ]
            
            new_row = f"|{'|'.join(new_values)}|\n" # Default format if no reference line is found
            
            # Grab column widths from the previous line to align the new row perfectly
            target_prev_idx = insert_idx - 1 if insert_idx != -1 else len(ip_lines) - 1
            if 0 <= target_prev_idx < len(ip_lines):
                prev_line = ip_lines[target_prev_idx].strip('\n')
                if prev_line.strip().startswith('|') and prev_line.strip().endswith('|'):
                    prev_cols = prev_line.strip().split('|')[1:-1]
                    if len(prev_cols) == len(new_values):
                        formatted_values = []
                        for prev_col, new_val in zip(prev_cols, new_values):
                            target_width = max(len(prev_col), len(new_val))
                            # Pads space evenly so pipes align
                            formatted_values.append(new_val.ljust(target_width))
                        new_row = f"|{'|'.join(formatted_values)}|\n"
                        
            if insert_idx != -1:
                ip_lines.insert(insert_idx, new_row)
            else:
                ip_lines.append(f"\n{new_row}")
                
            with open(ipaddr_path, "w") as f:
                f.writelines(ip_lines)
        else:
            print(f"\n[WARNING] Could not find IPADDR-{long_env}.md in expected paths. Skipping IP update.")

        # -------------------------------------------------------------
        # 4. RUN TERRAFORM PLAN
        # -------------------------------------------------------------
        tf_env = os.environ.copy()
        if gcp_sa:
            tf_env["GOOGLE_IMPERSONATE_SERVICE_ACCOUNT"] = gcp_sa
        tf_env["GIT_CONFIG_GLOBAL"] = isolated_gitconfig
        
        clean_plan, plan_failed = run_and_parse_tf_plan(plan_dir, tf_env, filename)
        
        pr_markdown = (
            f"<summary> Subnet Plan Output ({filename}) </summary>\n"
            f"<details>\n{clean_plan}\n</details>\n\n"
        )

        pr_body_path = os.path.join(run_clone_dir, ".nw_pr_body.md")
        with open(pr_body_path, "w") as f:
            f.write(pr_markdown.strip())

        return json.dumps({
            "status": "success",
            "plan_failed": plan_failed,
            "workspace_path": full_repo_path,
            "branch_name": branch_name,
            "app_acronym": app_acronym,
            "file_env": file_env,
            "jira_ticket": jira_ticket
        })
        
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def submit_network_pr(workspace_path: str, branch_name: str, jira_ticket: str, app_acronym: str, file_env: str) -> str:
    """
    Step 2: Commits and pushes the Subnet branch using the aggregated manual PR workflow.
    """
    try:
        print("\n" + "="*50)
        print(f"🚀 PUSHING BRANCH FOR {app_acronym.upper()} (SUBNET)")
        print("="*50)
        
        run_clone_dir = os.path.dirname(workspace_path)
        pr_body_path = os.path.join(run_clone_dir, ".nw_pr_body.md")
        
        with open(pr_body_path, "r") as f:
            pr_body = f.read()
            
        commit_msg_path = os.path.abspath(os.path.join(run_clone_dir, ".git_commit_msg.txt"))
        commit_title = f"{jira_ticket}: {app_acronym.upper()} {file_env} subnet creation"
        
        with open(commit_msg_path, "w") as f:
            f.write(f"{commit_title}\n\n{pr_body}")
        
        run_cmd("git add .", cwd=workspace_path)
        run_cmd(f'git commit -F "{commit_msg_path}"', cwd=workspace_path)
        run_cmd(f"git push origin {branch_name}", cwd=workspace_path)
        
        print(f"✅ Branch successfully pushed: {branch_name}\n")
        
        return f"Success! Branch `{branch_name}` pushed. The user can navigate to GitHub to open the PR with the subnet plan auto-filled."
        
    except Exception as e:
        print(f"\n❌ Error during git push: {str(e)}")
        return f"Push failed: {str(e)}"