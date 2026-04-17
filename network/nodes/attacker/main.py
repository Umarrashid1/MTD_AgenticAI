import os
import sys
import asyncio

from dotenv import load_dotenv
load_dotenv('/app/.env', override=True)

try:
    from cai.sdk.agents import Agent, Runner
    # Import the nmap function tool specifically
    from cai.tools.reconnaissance.nmap import nmap
    from cai.sdk.agents import enable_verbose_stdout_logging
except ImportError:
    print("[-] Error: Could not import CAI components. Ensure 'cai-framework' is installed.")
    sys.exit(1)

enable_verbose_stdout_logging()

async def main():
    print("[*] Booting CAI Autonomous Framework...")
    print(f"[*] Upstream AI: {os.environ.get('CAI_MODEL')}")

    # 2. Define the Agent
    agent = Agent(
        name="redteam_agent",
        model=os.environ["CAI_MODEL"],
        # Add the imported nmap function here
        tools=[nmap],
        instructions="""You are an autonomous penetration testing agent situated in an internal network subnet.
        Your objective is to perform reconnaissance on the 10.0.0.0/24 range.

        Rules of Engagement:
        1. You must use your built-in nmap tool to discover hosts and ports.
        2. Identify and map the network

        """
    )

    mission_trigger = "Perform a quick host discovery on 10.0.0.0/24. Do not scan all ports yet."
    print("\n[*] Initializing Agentic Loop...")

    # 3. Run the Agent Asynchronously
    try:
        result = await Runner.run(agent, input=mission_trigger)
        print("\n[*] Mission Complete. Final Output:")
        print(result.final_output)
    except Exception as e:
        print(f"\n[-] Agent loop terminated unexpectedly: {e}")


if __name__ == "__main__":
    asyncio.run(main())