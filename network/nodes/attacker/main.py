import asyncio
# Import Agent and Runner from the CAI SDK (not the generic 'agents' lib)
from cai.sdk.agents import Agent, Runner
# Import the actual nmap function tool
from cai.tools.reconnaissance.nmap import nmap


async def main():
    # DO NOT use NmapTool() - the function 'nmap' is already the tool.

    agent = Agent(
        name="DeepHat_Scanner",
        instructions="""You are a network mapping agent.
        Use your nmap tool to discover hosts on 10.0.0.0/24.
        Output a clean list of active IPs and open ports.""",
        tools=[nmap]  # Pass the function name directly
    )

    mission_trigger = "Scan 10.0.0.0/24 and map the network."

    try:
        # Pass the trigger directly to the runner
        result = await Runner.run(agent, mission_trigger)
        print(f"\n[*] Scan Result:\n{result.final_output}")
    except Exception as e:
        print(f"\n[-] Failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())