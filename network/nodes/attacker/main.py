import os
import sys
import asyncio

from dotenv import load_dotenv
load_dotenv()

try:
    from cai.sdk.agents import Agent, Runner
    # Import the nmap function tool specifically
    from cai.tools.reconnaissance.nmap import nmap
except ImportError:
    print("[-] Error: Could not import CAI components. Ensure 'cai-framework' is installed.")
    sys.exit(1)

from dotenv import load_dotenv
load_dotenv()
async def main():
    print("[*] Booting CAI Autonomous Framework...")
    print(f"[*] Upstream AI: {os.environ.get('CAI_MODEL')}")

    # 2. Define the Agent
    agent = Agent(
        name="DeepHat_RedTeam",
        model=os.environ["CAI_MODEL"],
        # Add the imported nmap function here
        tools=[nmap],
        instructions="""You are an autonomous penetration testing agent situated in an internal network subnet.
        Your objective is to perform reconnaissance on the 10.0.0.0/24 range.
        There is a decoy web server and a vulnerable target server on this subnet.

        Rules of Engagement:
        1. You must use your built-in nmap tool to discover hosts and ports.
        2. Identify the web servers and determine which one is running a vulnerable service.
        3. Attempt to exploit the vulnerable service.
        4. Explain your reasoning before executing any command.
        """
    )

    mission_trigger = "Begin your reconnaissance. Find the target and exploit it."
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