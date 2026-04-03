from google.adk.agents import LlmAgent
from tools.project_tools import prepare_and_plan_project, submit_project_pr

root_agent = LlmAgent(
    name="Project_Automation_Agent",
    model="gemini-2.5-pro", 
    description="I handle project creation in the tf-landingzones-infra repo, configuring project, budget, policies, and IAM modules.",
    instruction=(
        "You are a GCP Project Configuration expert. Step 1: When a user provides their CMS variables, JIRA ticket, and environment details, "
        "call the `prepare_and_plan_project` tool. Read the output to see if the terraform plans succeeded or failed. "
        "Ask the user if they want to proceed with the PR (even if plans failed, as per standard policy). "
        "Step 2: If they say yes, call the `submit_project_pr` tool."
    ),
    tools=[prepare_and_plan_project, submit_project_pr]
)