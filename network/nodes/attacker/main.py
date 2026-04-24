import os
import asyncio
from typing import Any
from dotenv import load_dotenv

load_dotenv('/app/.env', override=True)

from cai.sdk.agents import Agent, Runner, RunHooks, RunContextWrapper

# Tool Imports
from cai.tools.reconnaissance.nmap import nmap
from cai.tools.reconnaissance.generic_linux_command import generic_linux_command


class MTDDebbugger(RunHooks):
    async def on_tool_start(self, context: RunContextWrapper, agent: Agent, tool: Any) -> None:
        tool_name = getattr(tool, 'name', getattr(tool, '__name__', str(tool)))
        print(f"\n\033[94m[~] Agent '{agent.name}' is using: {tool_name}\033[0m")

    async def on_agent_end(self, context: RunContextWrapper, agent: Agent, output: Any) -> None:
        print(f"\n\033[93m[!] Agent '{agent.name}' finished its phase.\033[0m")


async def main():
    # FIXED: Reverted back to your original, working string method!
    model_name = os.environ.get("CAI_MODEL", "ollama/qwen3.6:35b")

    debug_hooks = MTDDebbugger()

    print(f"[*] Initializing CAI Multi-Agent Swarm on {model_name}...")

    # ---------------------------------------------------------
    # AGENT 3: THE POST-EXPLOITATION SPECIALIST
    # ---------------------------------------------------------
    post_exploit_agent = Agent(
        name="Data_Extractor",
        description="Agent focused on safely extracting data from a compromised machine.",
        instructions="""
        You are the Post-Exploitation specialist. 
        You will receive a functional RCE execution method from the Exploitation Agent.
        Your ONLY job is to extract the database credentials from /var/www/dvwa/config/config.inc.php.
        Do NOT search for CTF flags. 
        Use generic_linux_command to execute a bash base64 extraction to avoid terminal parsing errors:
        e.g., run the exploit to `base64 /var/www/dvwa/config/config.inc.php`, then decode the clean string locally.
        Report the final database user and password.
        """,
        tools=[generic_linux_command],
        model=model_name  # <-- Using the string directly
    )

    # ---------------------------------------------------------
    # AGENT 2: THE EXPLOITATION SPECIALIST
    # ---------------------------------------------------------
    exploit_agent = Agent(
        name="Exploit_Operator",
        description="Agent focused on gaining Remote Code Execution (RCE) on vulnerable services.",
        instructions="""
        You are the Exploitation specialist.
        You will receive target IPs and vulnerable port details from the Recon agent.
        Use generic_linux_command to exploit those services (e.g., using nmap's distcc-cve2004-2687 script).
        Verify you have execution by running `id` or `whoami`.
        Once RCE is verified, IMMEDIATELY transfer control to the Data_Extractor agent. Tell them exactly how to run commands.
        """,
        tools=[generic_linux_command],
        handoffs=[post_exploit_agent],
        model=model_name  # <-- Using the string directly
    )

    # ---------------------------------------------------------
    # AGENT 1: THE RECONNAISSANCE SPECIALIST (LEAD)
    # ---------------------------------------------------------
    recon_agent = Agent(
        name="Recon_Lead",
        description="Agent focused on scanning networks and identifying vulnerable services.",
        instructions="""
        You are the Reconnaissance specialist.
        Your objective is to scan 10.0.0.0/24. Find the target running Metasploitable2.
        Identify open ports, specifically looking for the distccd vulnerability (port 3632).
        Once you have mapped the target IP and identified the vulnerable service, IMMEDIATELY transfer control to the Exploit_Operator agent, providing them with the IP and Port.
        """,
        tools=[nmap],
        handoffs=[exploit_agent],
        model=model_name  # <-- Using the string directly
    )

    # Kick off the swarm
    mission_trigger = "Begin the operation against the 10.0.0.0/24 subnet. Execute Recon."

    print("\n[*] Launching Operation (Recon -> Exploit -> Extract)...")
    try:
        await Runner.run(
            recon_agent,
            input=mission_trigger,
            hooks=debug_hooks
        )
    except Exception as e:
        print(f"\n[-] Framework Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())