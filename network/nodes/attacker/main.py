import os
import asyncio
from typing import Any
from dotenv import load_dotenv
from pydantic import BaseModel
from dataclasses import dataclass  # <-- NEW IMPORT

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
# STRUCTURED DATA & MEMORY MODELS
# ---------------------------------------------------------
class IntelBriefing(BaseModel):
    summary: str


@dataclass
class SwarmState:
    """Holds global memory that agents can share during the run."""
    target_intel: str = "No intel provided yet."


# ---------------------------------------------------------
# UTILS & HOOKS
# ---------------------------------------------------------
class MTDDebbugger(RunHooks):
    async def on_agent_start(self, context: RunContextWrapper, agent: Agent) -> None:
        # 1. Resolve Instructions (System Prompt)
        # We check if it's a function (like our get_exploit_instructions) or a string
        instructions = agent.instructions
        if callable(instructions):
            instructions = instructions(context)

        print(f"\n\033[1;36m{'=' * 60}\033[0m")
        print(f"\033[1;36m[ACTIVE AGENT]: {agent.name}\033[0m")
        print(f"\n\033[1;35m[SYSTEM PROMPT]:\033[0m\n{instructions}")

        # 2. Print User/History (optional but helpful)
        # This shows the last message or trigger that started this agent turn
        print(f"\n\033[1;34m[LAST CONTEXT ITEM]:\033[0m")
        # In CAI, the context often holds the current turn's input
        print(f"{context.input_history if hasattr(context, 'input_history') else 'Initial Turn'}")
        print(f"\033[1;36m{'=' * 60}\033[0m\n")

    async def on_tool_start(self, context: RunContextWrapper, agent: Agent, tool: Any) -> None:
        tool_name = getattr(tool, 'name', getattr(tool, '__name__', str(tool)))
        print(f"\n\033[94m[~] Agent '{agent.name}' is using: {tool_name}\033[0m")

    async def on_tool_end(self, context: RunContextWrapper, agent: Agent, tool: Any, output: Any) -> None:
        tool_name = getattr(tool, 'name', getattr(tool, '__name__', str(tool)))
        print(f"\n\033[92m[<] Tool '{tool_name}' returned:\n{output}\033[0m")

    async def on_agent_end(self, context: RunContextWrapper, agent: Agent, output: Any) -> None:
        print(f"\n\033[93m[!] Agent '{agent.name}' finished its phase.\033[0m")

def scrub_nmap_history(data: Any) -> Any:
    """Surgically removes nmap tool calls from the context history."""
    filtered_pre = [item for item in data.pre_handoff_items if 'nmap' not in str(item).lower()]
    filtered_new = [item for item in data.new_items if 'nmap' not in str(item).lower()]

    return type(data)(
        input_history=data.input_history,
        pre_handoff_items=tuple(filtered_pre),
        new_items=tuple(filtered_new)
    )


async def receive_intel_briefing(context: RunContextWrapper[SwarmState], target_intel: IntelBriefing) -> None:
    """
    Catches the structured summary from the Recon agent and SAVES IT TO MEMORY.
    """
    print(
        f"\n\033[95m[*] INTER-AGENT COMMS: Recon passed the following intel to Exploit:\n{target_intel.summary}\033[0m")

    # Inject the intel into the Swarm's shared memory state
    if context.context:
        context.context.target_intel = target_intel.summary


# ---------------------------------------------------------
# DYNAMIC PROMPT FOR THE EXPLOIT OPERATOR
# ---------------------------------------------------------
# Added *args, **kwargs to absorb the second argument (the Agent object)
def get_exploit_instructions(context: RunContextWrapper[SwarmState], *args, **kwargs) -> str:
    """
    This function runs the exact moment the Exploit agent wakes up.
    It grabs the intel from memory and hardcodes it into the system prompt.
    """
    intel = context.context.target_intel if context.context else "Unknown Target"

    return f"""{RECOMMENDED_PROMPT_PREFIX}
        You are the Exploitation specialist. You have JUST received control of the operation.
        TARGET INTELLIGENCE BRIEFING:
        {intel}
       
        AUTONOMOUS EXPLOITATION WORKFLOW:
        1. Use the `execute_cli_command` tool to test payloads or techniques against the target IP listed above.
        2. Iterate. If a command fails, try a different method.

        CRITICAL RULES:
        - YOU DO NOT HAVE NMAP. DO NOT TRY TO RUN NMAP.
        - You ONLY have the `execute_cli_command` tool.
        - DO NOT call any handoff tools until you have established RCE.
        - Once you established RCE, call the `transfer_to_post_exploit_reporter` tool.
        """

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
            4. Do NOT attempt to run any more commands or tools. Just summarize what has been achieved.
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
        instructions=get_exploit_instructions,  # <--- Pass the function here, not a string!
        tools=[execute_cli_command],
        handoffs=[handoff(agent=post_exploit_agent)],
        model=model_name
    )

    # ---------------------------------------------------------
    # TACTICAL HANDOFF CONFIGURATION
    # ---------------------------------------------------------
    tactical_handoff = handoff(
        agent=exploit_agent,
        on_handoff=receive_intel_briefing,
        input_type=IntelBriefing,
        input_filter=scrub_nmap_history
    )

    # ---------------------------------------------------------
    # AGENT 1: THE RECONNAISSANCE SPECIALIST (LEAD)
    # ---------------------------------------------------------
    recon_agent = Agent(
        name="Recon_Lead",
        description="Agent focused on scanning networks and identifying services.",
        handoff_description="Lead agent that performs network scanning and reconnaissance.",
        instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
            You are the Reconnaissance specialist. Your objective is to find the vulnerable host.
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
        # Initialize the shared memory object
        swarm_state = SwarmState()

        # Create the streaming result object
        result = Runner.run_streamed(
            recon_agent,
            input=mission_trigger,
            hooks=debug_hooks,
            context=swarm_state  # <--- Pass the shared memory into the runner!
        )

        # Print raw text deltas in real-time
        async for event in result.stream_events():
            if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                print(event.data.delta, end="", flush=True)

    except Exception as e:
        print(f"\n\033[91m[-] Framework Error: {e}\033[0m")


if __name__ == "__main__":
    asyncio.run(main())