# Lumen Multi-Agent AI Orchestrator

This repository contains an AI-driven, multi-agent DevOps orchestration system built using the Google Agent Development Kit (ADK). It acts as a conversational interface to automate Google Cloud infrastructure provisioning, specifically handling App Onboarding (AD Groups/Folders) and Landing Zone module creation (Projects, Budgets, Policies, and IAM).

## 🏗️ Architecture

The system uses a **Router-Subagent** pattern:
* **`DevOps_Router` (`agent.py`):** The main entry point. It analyzes user requests and routes them to the appropriate specialist agent.
* **`Onboarding_Automation_Agent` (`onboarding_agent/agent.py`):** Specialist for creating Azure AD groups and Core IT infrastructure folders.
* **`Project_Automation_Agent` (`project_agent/agent.py`):** Specialist for generating Landing Zone project structures, resolving dynamic module versions, and generating `.tf` and `.tfvars` files.

## 📋 Prerequisites

Ensure you have the following installed on your local machine or Cloudtop:
* **Python 3.9+**
* **Git** (Configured for enterprise access if necessary)
* **Terraform** (>= 1.3.2)

## 📁 Repository Structure

```text
.
├── agent.py                  # ROOT: The DevOps Router (Entry point)
├── mappings.json             # Application acronyms and domain mappings
├── onboarding_agent/
│   └── agent.py              # Onboarding Sub-agent definition
├── project_agent/
│   └── agent.py              # Project Sub-agent definition
├── tools/
│   ├── app_onboarding.py     # Tool execution logic for Folders/AD Groups
│   └── project_tools.py      # Tool execution logic for Landing Zones (Git, TF Plans)
├── templates/
│   ├── tf_templates.py       # HCL generators for Onboarding
│   └── project_templates.py  # HCL generators for Landing Zones
└── utils/
    ├── github_utils.py       # API logic for resolving latest TF module versions (vM.N.O)
    └── system_utils.py       # Shell execution and file loading utilities
```

## ⚙️ Environment Variables

The agents interact with secure CenturyLink/Lumen GitHub repositories and Google Cloud. Authentication and configuration are managed via a `.env` file.

1. Copy the provided `.env.example` file to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and configure your credentials:
   * **`GITHUB_PAT`**: Your Personal Access Token for GitHub Enterprise (Required to fetch module versions and clone repos).
   * **`GCP_IMPERSONATE_SA`**: The GCP Service Account email to impersonate for Terraform execution.

*Note: The ADK framework will automatically load these variables when the server starts. Ensure `.env` is added to your `.gitignore` to prevent committing secrets to version control.*

## 🚀 Setup & Installation

**1. Create and activate a virtual environment (Recommended):**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**2. Install dependencies:**
```bash
pip install -r requirements.txt
```
*(Ensure `google-adk` or the equivalent ADK package is included in your requirements).*

## 🏃‍♂️ Running the Application

To start the ADK web server, run the following command from the **root directory** of this project (`tf-agent`):

```bash
adk web . --port 8000
```

1. Open your browser to `http://127.0.0.1:8000`.
2. The UI will present a list of loaded agents. Select **`DevOps_Router`**.
3. You are now ready to chat!

## 💬 Sample Prompts

### 1. Landing Zone Project Creation
Trigger the `Project_Automation_Agent` by providing standard CMS variables:

> "I need to create a new nonprod landing zone project for FAC. The JIRA ticket is SCPLZ-4325. 
> 
> Here are the required details:
> - Project Folder ID: 106228390504
> - Budget Email: test.user@lumen.com
> - tags_app_id: sysgen0787064400
> - tags_cost_app_owner_tech: charles_bushart__ac08676
> - tags_cost_app_owner_manager: mark_sanders__ac82378
> - tags_cost_budget_owner: mark_sanders__ac82378
> - tags_cost_cost_center: S0019742
> - tags_costdivision: IT & ENGINEERING
> - tags_environment: nonprod
> - tags_costbaseline: 2026
> 
> Please generate the terraform files and run the plans."

### 2. App Onboarding (AD Groups & Folders)
Trigger the `Onboarding_Automation_Agent` by asking for core folder setups:

> "Please create the AD groups and folder structures for the XYZ application in the prod environment. The owners are user1@lumen.com and user2@lumen.com. The Jira ticket is ITINFRA-1234."

