import os
import asyncio
from typing import Any
from dotenv import load_dotenv

load_dotenv('/app/.env', override=True)

# 1. IMPORTED `handoff` wrapper
from cai.sdk.agents import Agent, Runner, RunHooks, RunContextWrapper, handoff, enable_verbose_stdout_logging
from cai.sdk.agents.extensions import handoff_filters

# 2. IMPORTED the framework's recommended prompt prefix
from cai.sdk.agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

# Tool Imports
from cai.tools.reconnaissance.nmap import nmap
from cai.tools.misc.cli_utils import execute_cli_command
from cai.tools.web.search_web import make_google_search

enable_verbose_stdout_logging()

class MTDDebbugger(RunHooks):
    async def on_tool_start(self, context: RunContextWrapper, agent: Agent, tool: Any) -> None:
        tool_name = getattr(tool, 'name', getattr(tool, '__name__', str(tool)))
        print(f"\n\033[94m[~] Agent '{agent.name}' is using: {tool_name}\033[0m")

    async def on_tool_end(self, context: RunContextWrapper, agent: Agent, tool: Any, output: Any) -> None:
        tool_name = getattr(tool, 'name', getattr(tool, '__name__', str(tool)))
        print(f"\n\033[92m[<] Tool '{tool_name}' returned:\n{output}\033[0m")

    async def on_agent_end(self, context: RunContextWrapper, agent: Agent, output: Any) -> None:
        print(f"\n\033[93m[!] Agent '{agent.name}' finished its phase.\033[0m")

async def main():
    model_name = os.environ.get("CAI_MODEL", "ollama/qwen3.6:35b")
    debug_hooks = MTDDebbugger()

    print(f"[*] Initializing CAI Multi-Agent Swarm on {model_name}...")

    # ---------------------------------------------------------
    # AGENT 3: THE POST-EXPLOITATION SPECIALIST
    # ---------------------------------------------------------

    post_exploit_agent = Agent(
        name="Post_Exploit_Reporter",
        description="Agent focused on reading configuration files and summarizing the attack chain.",
        handoff_description="Specialized agent for extracting credentials and writing the final exploitation report.",
        instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
            You are the Post-Exploitation Reporter. You have JUST received control of the operation.

            Step 1: Read the chat history to understand how the Exploit_Operator successfully gained Remote Code Execution (RCE) on the target.
            Step 2: Use the execute_cli_command tool to read the contents of /var/www/dvwa/config/config.inc.php (e.g., using the `cat` command).
            Step 3: Extract the database user and password from the configuration file.

            Final Step: Generate a concise 'Post-Exploitation Report' that tells the user exactly what happened. Your report must include:
            - The target IP and vulnerable web port.
            - A brief summary of the exploit/command used to gain RCE.
            - The proof of execution (e.g., the user the server is running as).
            - The extracted database credentials.
            """,
        tools=[execute_cli_command],
        model=model_name
    )

    # ---------------------------------------------------------
    # AGENT 2: THE EXPLOITATION SPECIALIST
    # ---------------------------------------------------------
    exploit_agent = Agent(
        name="Exploit_Operator",
        description="Agent focused on gaining Remote Code Execution (RCE) on vulnerable services.",
        handoff_description="Specialized agent for running exploitation commands to gain RCE.",
        instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
            You are the Exploitation specialist. 
            Read the chat history to find the target IP and open ports provided by the Recon agent.

            AUTONOMOUS EXPLOITATION WORKFLOW:
            1. If you are unsure how to exploit the service (e.g., Apache on port 80, WebDAV, or DVWA), use the `make_google_search` tool. 
               - Pass the current context and ask specifically for "Command line techniques using curl to exploit [Service Name]".
            2. Read the intelligence provided by the search tool.
            3. Use the `execute_cli_command` tool to test the payloads or techniques you just learned against the target.
            4. Iterate. If a command fails, search for a different method and try again.

            CRITICAL RULES:
            - When using execute_cli_command, DO NOT provide a `session_id`.
            - You MUST establish RCE or verify your exploit works (e.g., by reading a file or running `whoami`) before handing off.

            Once you have successfully exploited the target, summarize your attack path. 
            Include the vulnerable service, the exploit technique used, and the proof of execution. Then hand off to the Post-Exploitation agent for credential extraction and final reporting.
            """,
        # GIVE IT BOTH TOOLS: One for thinking, one for doing
        tools=[make_google_search, execute_cli_command],
        handoffs=[handoff(agent=post_exploit_agent, input_filter=handoff_filters.remove_all_tools)],
        model=model_name
    )

    # ---------------------------------------------------------
    # AGENT 1: THE RECONNAISSANCE SPECIALIST (LEAD)
    # ---------------------------------------------------------
    recon_agent = Agent(
        name="Recon_Lead",
        description="Agent focused on scanning networks and identifying vulnerable services.",
        handoff_description="Lead agent that performs network scanning and reconnaissance.", # <-- Added handoff_description
        instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
        You are the Reconnaissance specialist.
        Your objective is to scan 10.0.0.0/24. Find the target running Metasploitable2.
        Your IP is 10.0.0.11 so dont waste time scanning yourself. Focus on the other IPs in the subnet.
        Start with a fast ping sweep to identify live hosts, then perform a more detailed scan on any responsive IPs to enumerate services and versions.
        Identify open ports, specifically looking for the vulnerability.
        Once you have mapped the target IP and identified the vulnerable service, output a summary.        """,
        tools=[nmap],
        handoffs=[handoff(agent=exploit_agent, input_filter=handoff_filters.remove_all_tools)],
        model=model_name
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