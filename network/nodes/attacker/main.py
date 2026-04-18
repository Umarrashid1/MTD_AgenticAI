import os
import sys
import asyncio
from dotenv import load_dotenv

load_dotenv('/app/.env', override=True)

try:
    from cai.sdk.agents import Agent, Runner, AgentHooks
    from cai.tools.reconnaissance.nmap import nmap
except ImportError:
    print("[-] Error: Could not import CAI components.")
    sys.exit(1)

class VerboseInformer(AgentHooks):
    async def on_tool_end(self, context, tool_call, result):
        """Triggers when nmap finishes but BEFORE it goes to the LLM"""
        print(f"\n\033[92m[DEBUG] Tool '{tool_call.name}' finished.\033[0m")
        print(f"\033[94m[RAW TOOL OUTPUT]:\n{result}\033[0m\n")

    async def on_turn_end(self, context, turn_output):
        """Triggers after the LLM responds but BEFORE the next turn starts"""
        print(f"\n\033[93m[DEBUG] LLM Response for this turn:\033[0m")
        print(f"{turn_output.text}\n")

async def main():
    agent = Agent(
        name="mtd_redteam_specialist",
        model=os.environ["CAI_MODEL"],
        tools=[nmap],
        hooks=VerboseInformer(), # Attach the hook here
        instructions="""Locate the vulnerable server. 
        Be concise in your reasoning to avoid context overflow."""
    )

    mission_trigger = "Scan 10.0.0.0/24. Find the vulnerable host."

    try:
        # Run with the hook active
        result = await Runner.run(agent, input=mission_trigger)
        print("\n[*] Mission Complete.")
    except Exception as e:
        print(f"\n[-] Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())