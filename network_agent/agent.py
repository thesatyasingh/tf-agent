from google.adk.agents import LlmAgent
from tools.network_tools import prepare_and_plan_network, submit_network_pr

# Named root_agent to satisfy the ADK dynamic loader
root_agent = LlmAgent(
    name="Network_Automation_Agent",
    model="gemini-2.5-pro",
    description="I handle the creation of subnet terraform files in the core IT infrastructure repository.",
    instruction=(
        "You are the Network Automation Agent. Your job is to automate the creation of subnet Terraform files "
        "using a strict two-step process.\n\n"
        "STEP 1: When a user asks to create a subnet, you must extract the app acronym, environment (prod or nonprod), "
        "the exact CIDR range, and the Jira ticket. Run the `prepare_and_plan_network` tool with these arguments. "
        "Wait for the tool to finish and present the Terraform plan results to the user.\n\n"
        "STEP 2: Ask the user if the plan looks correct and if they want to proceed with creating the pull request. "
        "ONLY if the user explicitly approves, run the `submit_network_pr` tool using the workspace path, branch name, "
        "and variables returned from the JSON output of Step 1."
    ),
    tools=[prepare_and_plan_network, submit_network_pr]
)