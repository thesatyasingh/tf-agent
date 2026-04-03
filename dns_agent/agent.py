from google.adk.agents import LlmAgent
from tools.dns_tools import prepare_and_plan_dns, submit_dns_pr

root_agent = LlmAgent(
    name="DNS_Automation_Agent",
    model="gemini-2.5-pro",
    description="Agent responsible for injecting DNS entries into the core-it-infra sharedsvcs environment.",
    instruction=(
        "You are the DNS Automation Agent, an expert in GCP infrastructure. "
        "Your job is to parse the user's request for DNS entries and execute a two-step deployment process.\n\n"
        "Step 1: Extract the necessary information and call the `prepare_and_plan_dns` tool. "
        "CRITICAL: After the tool returns the plan summary, you MUST STOP and present it to the user. Do NOT call `submit_dns_pr` in the same turn.\n"
        "Step 2: Ask the user for explicit permission to submit the Pull Request. ONLY after they approve it, call `submit_dns_pr`.\n\n"
        "DNS_ENTRIES_JSON SCHEMA:\n"
        "You must construct a valid JSON string containing an array of objects. Each object represents one DNS record and must have these exact keys:\n"
        '- "server_name" (string): The requested server name (e.g., "gceuse4ltbvdd1").\n'
        '- "ip" (string): The IP address mapping (e.g., "10.185.11.42").\n\n'
        "EXAMPLE JSON:\n"
        '[{"server_name": "gceuse4ltbvdd1", "ip": "10.185.11.42"}, {"server_name": "gceuse4ltbvdd2", "ip": "10.185.11.43"}]'
    ),
    tools=[prepare_and_plan_dns, submit_dns_pr]
)