import os
import asyncio
from typing import Any
from dotenv import load_dotenv
from pydantic import BaseModel

# Import the specific Pydantic model needed for raw streaming
from openai.types.responses import ResponseTextDeltaEvent

load_dotenv('/app/.env', override=True)

# CAI Imports
from cai.sdk.agents import Agent, Runner, RunHooks, RunContextWrapper, handoff, enable_verbose_stdout_logging
from cai.sdk.agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

# Tool Imports
from cai.tools.reconnaissance.nmap import nmap
from cai.tools.misc.cli_utils import execute_cli_command

enable_verbose_stdout_logging()

# ---------------------------------------------------------
# STRUCTURED DATA MODELS
# ---------------------------------------------------------
class IntelBriefing(BaseModel):
    """
    Structured payload for transferring intelligence between agents.
    Using a Pydantic model prevents validation errors if the LLM
    outputs JSON (which tool-calling models prefer to do).
    """
    summary: str

# ---------------------------------------------------------
# UTILS & HOOKS
# ---------------------------------------------------------
class MTDDebbugger(RunHooks):
    async def on_tool_start(self, context: RunContextWrapper, agent: Agent, tool: Any) -> None:
        tool_name = getattr(tool, 'name', getattr(tool, '__name__', str(tool)))
        print(f"\n\033[94m[~] Agent '{agent.name}' is using: {tool_name}\033[0m")

    async def on_tool_end(self, context: RunContextWrapper, agent: Agent, tool: Any, output: Any) -> None:
        tool_name = getattr(tool, 'name', getattr(tool, '__name__', str(tool)))
        print(f"\n\033[92m[<] Tool '{tool_name}' returned:\n{output}\033[0m")

    async def on_agent_end(self, context: RunContextWrapper, agent: Agent, output: Any) -> None:
        print(f"\n\033[93m[!] Agent '{agent.name}' finished its phase.\033[0m")


def scrub_nmap_history(data: Any) -> Any:
    """
    Surgically removes nmap tool calls from the context history.
    This prevents the Exploit_Operator from trying to copy the Recon_Lead.
    """
    filtered_pre = [item for item in data.pre_handoff_items if 'nmap' not in str(item).lower()]
    filtered_new = [item for item in data.new_items if 'nmap' not in str(item).lower()]

    return type(data)(
        input_history=data.input_history,
        pre_handoff_items=tuple(filtered_pre),
        new_items=tuple(filtered_new)
    )

async def receive_intel_briefing(context: RunContextWrapper[Any], target_intel: IntelBriefing) -> None:
    """
    Catches the structured summary from the Recon agent.
    """
    print(f"\n\033[95m[*] INTER-AGENT COMMS: Recon passed the following intel to Exploit:\n{target_intel.summary}\033[0m")


async def main():
    model_name = os.environ.get("CAI_MODEL", "ollama/qwen3.6:35b")
    debug_hooks = MTDDebbugger()

    print(f"\n[*] Initializing CAI Multi-Agent Swarm on {model_name}...")

    # ---------------------------------------------------------
    # AGENT 3: THE POST-EXPLOITATION SPECIALIST
    # ---------------------------------------------------------
    post_exploit_agent = Agent(
        name="Post_Exploit_Reporter",
        description="Summarizes the attack chain for the final user report.",
        instructions="""
            You are the Final Reporter. 
            1. Review the entire conversation history.
            2. Identify: The target IP, the vulnerability exploited, and any credentials found.
            3. Format this into a professional 'Penetration Testing Summary'.
            4. Do NOT attempt to run any more commands. Just summarize what has been achieved.
        """,
        tools=[],
        model=model_name
    )

    # ---------------------------------------------------------
    # AGENT 2: THE EXPLOITATION SPECIALIST
    # ---------------------------------------------------------
    exploit_agent = Agent(
        name="Exploit_Operator",
        description="Agent focused on gaining Remote Code Execution (RCE).",
        handoff_description="Specialized agent for running exploitation commands to gain RCE.",
        instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
            You are the Exploitation specialist. You have JUST received control of the operation.
            Look at the intel briefing provided in the handoff to find the target IP and open ports.

            AUTONOMOUS EXPLOITATION WORKFLOW:
            1. Use the `execute_cli_command` tool to test payloads or techniques against the target.
            2. Iterate. If a command fails, try a different method.

            CRITICAL RULES:
            - YOU DO NOT HAVE NMAP. DO NOT TRY TO RUN NMAP.
            - You ONLY have the `execute_cli_command` tool.
            - DO NOT call any handoff tools until you have established RCE.
            - Once you established RCE, call the `transfer_to_post_exploit_reporter` tool.
            """,
        tools=[execute_cli_command],
        handoffs=[handoff(agent=post_exploit_agent)],
        model=model_name
    )

    # ---------------------------------------------------------
    # TACTICAL HANDOFF CONFIGURATION (The "shift change")
    # ---------------------------------------------------------
    tactical_handoff = handoff(
        agent=exploit_agent,
        on_handoff=receive_intel_briefing,
        input_type=IntelBriefing,          # Uses Pydantic for bulletproof validation
        input_filter=scrub_nmap_history    # Wipes the nmap noise
    )

    # ---------------------------------------------------------
    # AGENT 1: THE RECONNAISSANCE SPECIALIST (LEAD)
    # ---------------------------------------------------------
    recon_agent = Agent(
        name="Recon_Lead",
        description="Agent focused on scanning networks and identifying services.",
        handoff_description="Lead agent that performs network scanning and reconnaissance.",
        instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
            You are the Reconnaissance specialist. Your objective is to find the host running Metasploitable2.
            Your IP is 10.0.0.11. DO NOT scan your own IP.

            CRITICAL RULES FOR NMAP:
            1. STEP 1: Run a fast ping sweep: `nmap -sn 10.0.0.0/24`
            2. STEP 2: Run a targeted port scan ONLY on the live IPs found (excluding 10.0.0.11) using: `-T5 --min-rate 10000 -p 80,21,22`
            3. STOP SCANNING once you identify a target with open ports.

            HANDOFF INSTRUCTIONS:
            Once you find the target IP, immediately call the handoff tool. 
            You MUST provide a 'summary' field containing:
            "Target IP is [IP]. Open ports: [Ports]."
        """,
        tools=[nmap],
        handoffs=[tactical_handoff],
        model=model_name
    )

    # Kick off the swarm
    mission_trigger = "Begin the operation against the 10.0.0.0/24 subnet. Execute Recon."
    print("[*] Launching Operation (Recon -> Exploit -> Extract)...\n")

    try:
        # Create the streaming result object
        result = Runner.run_streamed(
            recon_agent,
            input=mission_trigger,
            hooks=debug_hooks
        )

        # Print raw text deltas in real-time
        async for event in result.stream_events():
            if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                print(event.data.delta, end="", flush=True)

    except Exception as e:
        print(f"\n\033[91m[-] Framework Error: {e}\033[0m")


if __name__ == "__main__":
    asyncio.run(main())