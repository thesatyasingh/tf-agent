from google.adk.agents import LlmAgent
from onboarding_agent.agent import root_agent as onboarding_expert
from project_agent.agent import root_agent as project_expert
from network_agent.agent import root_agent as network_expert
from gce_agent.agent import root_agent as gce_expert
from dns_agent.agent import root_agent as dns_expert

agent = LlmAgent(
    name="DevOps_Router",
    model="gemini-2.5-pro",
    description="I route user requests to the correct Terraform automation expert.",
    instruction=(
        "You are the DevOps Orchestrator. Analyze the user's request.\n"
        "If they need to create AD Groups or core infrastructure folders, transfer the conversation to the Onboarding_Automation_Agent.\n"
        "If they need to create a project, budget, policies, and IAM in the landing zone repository, transfer the conversation to the Project_Automation_Agent.\n"
        "If they need to create a subnet Terraform file for an application in the core IT infrastructure repository, transfer the conversation to the Network_Automation_Agent.\n"
        "If they need to provision Virtual Machines, GCE instances, or add data disks, transfer the conversation to the GCE_Automation_Agent.\n"
        "If they need to add DNS entries or map server names to IPs, transfer the conversation to the DNS_Automation_Agent." # <-- Add this rule
    ),
    sub_agents=[onboarding_expert, project_expert, network_expert, gce_expert, dns_expert] # <-- Add to array
)