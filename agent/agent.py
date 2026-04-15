import os
import asyncio
# Import the specific tools from the directory you found
from cai.tools.reconnaissance import NmapTool
from agents import Agent, Runner


# Disable the tracing
os.environ["OTEL_SDK_DISABLED"] = "true"

async def main():
    # 1. Instantiate the actual tool
    # This allows the AI to execute 'nmap' on your host
    network_scanner = NmapTool()

    # 2. Add the tool to the Agent
    agent = Agent(
        name="DeepHat_Scanner",
        tools=[network_scanner], # THIS IS CRITICAL
        instructions="""You are a network mapping agent.
        Use your nmap tool to discover hosts on 10.0.0.0/24.
        Output a clean list of active IPs and open ports.
        Do not explain how nmap works, just execute it."""
    )

    mission_trigger = "Scan the 10.0.0.0/24 subnet and map the services."

    try:
        # The Runner now sees the 'tools' and allows the LLM to call them
        result = await Runner.run(agent, input=mission_trigger)
        print(f"\n[*] Scan Result:\n{result.final_output}")
    except Exception as e:
        print(f"\n[-] Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())