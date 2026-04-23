import os
import sys
import asyncio
from typing import Any
from dotenv import load_dotenv

load_dotenv('/app/.env', override=True)

from cai.sdk.agents import Agent, Runner, RunHooks, RunContextWrapper, enable_verbose_stdout_logging
from cai.tools.reconnaissance.nmap import nmap

enable_verbose_stdout_logging()


class MTDDebbugger(RunHooks):
    """
    Hook to intercept and print exactly what nmap sends back
    and how the LLM responds. Essential for tracking MTD state changes.
    """

    async def on_tool_start(self, context: RunContextWrapper, agent: Agent, tool: Any) -> None:
        print(f"\n\033[94m[~] Agent '{agent.name}' is executing: {tool.name}\033[0m")

    async def on_tool_end(self, context: RunContextWrapper, agent: Agent, tool: Any, result: str) -> None:
        print(f"\n\033[92m[+] TOOL OUTPUT (Raw Result):\033[0m")
        print("--------------------------------------------------")
        print(result)
        print("--------------------------------------------------")
        print(f"\033[92m[Tokens used: {context.usage.total_tokens}]\033[0m\n")

    async def on_agent_end(self, context: RunContextWrapper, agent: Agent, output: Any) -> None:
        print(f"\n\033[93m[!] Agent '{agent.name}' Turn Finished.\033[0m")
        print(f"Final Output: {output}")


async def main():
    model_name = os.environ.get("CAI_MODEL", "gemini-1.5-pro")  # Defaulting just in case

    debug_hooks = MTDDebbugger()

    # THE FIX: Instructing the LLM on MTD physics and behavior
    mtd_instructions = """
    You are an elite Red Team specialist operating in a Software-Defined Network.

    """

    agent = Agent(
        name="redteam_mtd_specialist",
        model=model_name,
        tools=[nmap],
        instructions=mtd_instructions
    )

    # Trigger forces the agent to establish a fingerprint right away
    mission_trigger = """
        Perform a comprehensive scan of the 10.0.0.0/24 subnet. 
        1. Identify all active hosts and their open ports.
        2. Determine service versions and potential OS types for any discovered targets.
        3. Summarize the attack surface and identify the most high-value targets for further exploitation.
        """

    print(f"[*] Starting Agentic Loop against MTD Network (Model: {model_name})...")

    try:
        await Runner.run(
            agent,
            input=mission_trigger,
            hooks=debug_hooks
        )
    except Exception as e:
        print(f"\n[-] Framework Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())