import os
import sys
import asyncio
from typing import Any
from dotenv import load_dotenv

load_dotenv('/app/.env', override=True)

# Use your existing imports
from cai.sdk.agents import Agent, Runner, RunHooks, RunContextWrapper, enable_verbose_stdout_logging
from cai.tools.reconnaissance.nmap import nmap

enable_verbose_stdout_logging()



class MTDDebbugger(RunHooks):
    """
    Hook to intercept and print exactly what nmap sends back
    and how the LLM responds.
    """

    async def on_tool_start(self, context: RunContextWrapper, agent: Agent, tool: Any) -> None:
        print(f"\n\033[94m[~] Agent '{agent.name}' is running tool: {tool.name}\033[0m")

    async def on_tool_end(self, context: RunContextWrapper, agent: Agent, tool: Any, result: str) -> None:
        print(f"\n\033[92m[+] TOOL OUTPUT (Raw Nmap Result):\033[0m")
        print("--------------------------------------------------")
        # This is where we see what the tool actually found
        print(result)
        print("--------------------------------------------------")
        print(f"\033[92m[Tokens used so far: {context.usage.total_tokens}]\033[0m\n")

    async def on_agent_end(self, context: RunContextWrapper, agent: Agent, output: Any) -> None:
        print(f"\n\033[93m[!] Agent '{agent.name}' Turn Finished.\033[0m")
        print(f"Final Output: {output}")


async def main():
    # Use your original model from environment
    model_name = os.environ["CAI_MODEL"]

    debug_hooks = MTDDebbugger()

    agent = Agent(
        name="redteam_specialist",
        model=model_name,
        tools=[nmap],
        instructions="""Locate the vulnerable server in 10.0.0.0/24. 
        Focus on identifying active services. Keep reasoning short."""
    )

    mission_trigger = "Perform a quick scan of 10.0.0.0/24 and find the vulnerable host."

    print(f"[*] Starting Agentic Loop (Model: {model_name})...")

    try:
        # Note: Hooks are passed to Runner.run, not the Agent constructor
        await Runner.run(
            agent,
            input=mission_trigger,
            hooks=debug_hooks
        )
    except Exception as e:
        print(f"\n[-] Framework Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())