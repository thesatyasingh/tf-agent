import os
import json
from datetime import datetime
from utils.system_utils import run_cmd
from tools.network_tools import run_and_parse_tf_plan

def prepare_and_plan_dns(app_acronym: str, environment: str, jira_ticket: str, dns_entries_json: str) -> str:
    """
    Clones Core IT Infra repo, injects DNS entries into sharedsvcs, updates CHANGELOG, and plans.
    dns_entries_json should be a list: [{"server_name": "...", "ip": "..."}, ...]
    """
    github_token = os.environ.get("GITHUB_PAT")
    gcp_sa = os.environ.get("GCP_IMPERSONATE_SA")
    github_org = "CenturyLink"
    repo_name = "tf-core-it-infra--gcp-coreit-infra"
    
    try:
        dns_configs = json.loads(dns_entries_json)
        acronym = app_acronym.lower()
        long_env = "prod" if environment.lower() == "prod" else "nonprod"
        
        date_str = datetime.now().strftime("%y%m%d")
        branch_name = f"branch/{date_str}-{jira_ticket}-{acronym}-{long_env}-dns"
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
        base_dir = os.path.join(full_repo_path, "root-lz", "core-shared", "network", "prj-lmn-core-nw-sharedsvcs-01")
        tf_dir = os.path.join(base_dir, "project")
        dns_module_dir = os.path.join(tf_dir, "modules", "dns", "mod-prj-intranet-corp-gcl")
        
        # -------------------------------------------------------------
        # 1. UPDATE DNS TERRAFORM FILE
        # -------------------------------------------------------------
        tf_file_name = "gclcorp-prod.tf" if long_env == "prod" else "gclcorp-nonprod.tf"
        tf_file_path = os.path.join(dns_module_dir, tf_file_name)
        
        target_map_start = "prod_non_wc_hosts = tomap({" if long_env == "prod" else "np_hosts = tomap({"
        
        if os.path.exists(tf_file_path):
            with open(tf_file_path, "r") as f:
                tf_lines = f.readlines()
                
            insert_idx = -1
            in_target_map = False
            for i, line in enumerate(tf_lines):
                if target_map_start in line:
                    in_target_map = True
                elif in_target_map and line.strip() == "})":
                    insert_idx = i
                    break
            
            if insert_idx != -1:
                # FIX 1: Move insert index UP to skip over any existing blank lines
                while insert_idx > 0 and tf_lines[insert_idx - 1].strip() == "":
                    insert_idx -= 1

                # FIX 2: Dynamically find the exact column index of the '=' from the line above it
                target_equals_index = 30  # Fallback default
                if insert_idx > 0:
                    prev_line_raw = tf_lines[insert_idx - 1]
                    if "=" in prev_line_raw:
                        target_equals_index = prev_line_raw.index("=")

                new_entries = []
                for entry in dns_configs:
                    server_str = f'"{entry["server_name"]}"'
                    ip_str = f'"{entry["ip"]}",'
                    
                    # Construct line and pad spaces so the '=' lands exactly at target_equals_index
                    prefix = f"    {server_str}"
                    spaces_to_add = target_equals_index - len(prefix)
                    if spaces_to_add < 1:
                        spaces_to_add = 1
                        
                    formatted_line = f"{prefix}{' ' * spaces_to_add}= {ip_str}\n"
                    new_entries.append(formatted_line)
                    
                tf_lines[insert_idx:insert_idx] = new_entries
                
                with open(tf_file_path, "w") as f:
                    f.writelines(tf_lines)
            else:
                return json.dumps({"status": "error", "message": f"Could not find {target_map_start} block in {tf_file_name}"})
        else:
            return json.dumps({"status": "error", "message": f"DNS File {tf_file_path} does not exist."})

        # -------------------------------------------------------------
        # 2. UPDATE CHANGELOG.MD
        # -------------------------------------------------------------
        changelog_path = os.path.join(base_dir, "CHANGELOG.md")
        if os.path.exists(changelog_path):
            with open(changelog_path, "r") as f:
                cl_lines = f.readlines()
            
            new_cl_entry = f"* [{jira_ticket}](https://lumen.atlassian.net/browse/{jira_ticket}) - {date_str}\n  * Adding {acronym} {long_env} DNS entries\n"
            
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

        # -------------------------------------------------------------
        # 3. RUN TERRAFORM PLAN
        # -------------------------------------------------------------
        clean_plan, plan_failed = run_and_parse_tf_plan(tf_dir, tf_env, f"DNS_{long_env}")
        
        pr_markdown = (
            f"<summary> DNS Plan Output ({tf_file_name}) </summary>\n"
            f"<details>\n{clean_plan}\n</details>\n\n"
        )

        pr_body_path = os.path.join(run_clone_dir, ".dns_pr_body.md")
        with open(pr_body_path, "w") as f:
            f.write(pr_markdown.strip())

        return json.dumps({
            "status": "success",
            "plan_failed": plan_failed,
            "workspace_path": full_repo_path,
            "branch_name": branch_name,
            "app_acronym": acronym,
            "long_env": long_env,
            "jira_ticket": jira_ticket
        })
        
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def submit_dns_pr(workspace_path: str, branch_name: str, jira_ticket: str, app_acronym: str, long_env: str) -> str:
    """Commits and pushes the DNS branch."""
    try:
        run_clone_dir = os.path.dirname(workspace_path)
        with open(os.path.join(run_clone_dir, ".dns_pr_body.md"), "r") as f: 
            pr_body = f.read()
            
        commit_msg_path = os.path.abspath(os.path.join(run_clone_dir, ".git_commit_msg.txt"))
        with open(commit_msg_path, "w") as f: 
            f.write(f"{jira_ticket}: {app_acronym.upper()} {long_env} DNS entries\n\n{pr_body}")
        
        run_cmd("git add .", cwd=workspace_path)
        run_cmd(f'git commit -F "{commit_msg_path}"', cwd=workspace_path)
        run_cmd(f"git push origin {branch_name}", cwd=workspace_path)
        return f"Success! Branch `{branch_name}` pushed to GitHub."
    except Exception as e:
        return f"Push failed: {str(e)}"