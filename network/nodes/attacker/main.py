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
    You are an elite Red Team specialist operating in a Moving Target Defense (MTD) Software-Defined Network.

    CRITICAL ENVIRONMENT RULES:
    1. IPs and MAC addresses SHUFFLE frequently. Reconnaissance data decays in minutes.
    2. DO NOT rely on historical IPs. If a connection or exploit fails, assume the target has migrated and RE-SCAN the subnet immediately.
    3. Track targets by FINGERPRINT, not IP. Look for unique combinations of open ports, service banners, or OS signatures.
    4. When scanning, prioritize SPEED. Use aggressive timing (e.g., -T4 or -T5) and target specific ports to minimize the scan window. Broad scans take too long and the target will move before you finish.

    Mission Guidelines:
    Keep your reasoning brief. Identify the target fingerprint, locate its current IP, and maintain tracking as it moves.
    """

    agent = Agent(
        name="redteam_mtd_specialist",
        model=model_name,
        tools=[nmap],
        instructions=mtd_instructions
    )

    # Trigger forces the agent to establish a fingerprint right away
    mission_trigger = """
    Perform a high-speed scan of 10.0.0.0/24. 
    1. Identify the unique service fingerprint of the vulnerable host.
    2. Note its current IP. 
    3. Provide a brief summary of how you will recognize this host when its IP shuffles.
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