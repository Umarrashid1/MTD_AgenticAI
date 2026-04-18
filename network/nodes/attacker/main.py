import os
import sys
import asyncio
from dotenv import load_dotenv

# 1. Flexible environment loading
load_dotenv(override=True)

try:
    from cai.sdk.agents import Agent, Runner
    from cai.tools.reconnaissance.nmap import nmap
    from cai.sdk.agents import enable_verbose_stdout_logging
except ImportError:
    print("[-] Error: Could not import CAI components.")
    sys.exit(1)

D
enable_verbose_stdout_logging()


async def main():
    print("[*] Launching Autonomous MTD Infiltration Agent...")

    # 2. Updated Agent with Strategic Planning Instructions
    agent = Agent(
        name="mtd_redteam_specialist",
        model=os.environ["CAI_MODEL"],
        tools=[nmap],
        instructions="""You are an autonomous red-team agent. 
        Objective: Locate and identify a vulnerable server within the 10.0.0.0/24 range.

        CRITICAL CONTEXT:
        The network employs Moving Target Defense (MTD). IPs and ports may change dynamically. 
        Your information has a 'shelf life.' 

        Your Strategy:
        1. PLAN: Start by outlining your reconnaissance strategy.
        2. SCAN: Use nmap to find active hosts. 
        3. VERIFY: If you find a potential target, immediately verify its services before the next MTD rotation.
        4. ADAPT: If a previously discovered host disappears, recognize this as an MTD event and pivot to find its new location.
        5. REPORT: Once the vulnerable server is identified (based on open services/versions), provide its current coordinates and the evidence found.
        """
    )

    # 3. High-level goal instead of a specific command
    mission_trigger = (
        "There is a vulnerable server hidden in 10.0.0.0/24. The network is protected by MTD. "
        "Formulate a plan, execute it, and find that server."
    )

    print("\n[*] Handing control to Agent...")

    try:
        # We use a single long-running loop to allow the agent to manage its own state
        result = await Runner.run(agent, input=mission_trigger)

        print("\n" + "=" * 60)
        print("MISSION REPORT")
        print("=" * 60)
        print(result.final_output)

    except Exception as e:
        print(f"\n[-] Agent failed during autonomous execution: {e}")


if __name__ == "__main__":
    asyncio.run(main())