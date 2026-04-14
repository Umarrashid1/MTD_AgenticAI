import os
import sys
import asyncio

# Correct production import path for the pip package
try:
    from cai.sdk.agents import Agent, Runner
except ImportError:
    print("[-] Error: Could not import CAI components. Ensure 'cai-framework' is installed.")
    sys.exit(1)

# 1. Force the LiteLLM/Ollama Routing Bridge
os.environ["OPENAI_API_BASE"] = "http://172.17.0.1:11434/v1"
os.environ["OPENAI_API_KEY"] = "sk-dummy-key-not-used"
os.environ["CAI_MODEL"] = "ollama/DeepHat"


async def main():
    print("[*] Booting CAI Autonomous Framework...")
    print(f"[*] Upstream AI: {os.environ.get('CAI_MODEL')}")

    # 2. Define the Agent strictly using its built-in OS interaction tools
    agent = Agent(
        name="DeepHat_RedTeam",
        instructions="""You are an autonomous penetration testing agent situated in an internal network subnet.
        Your objective is to perform reconnaissance on the 10.0.0.0/24 range.
        There is a decoy web server and a vulnerable target server on this subnet.

        Rules of Engagement:
        1. You must use your built-in linux terminal tools to run native Kali commands (e.g., nmap, curl, nc).
        2. Identify the web servers and determine which one is running a vulnerable service.
        3. Attempt to exploit the vulnerable service.
        4. Explain your reasoning before executing any command.
        """
    )

    mission_trigger = "Begin your reconnaissance. Find the target and exploit it."
    print("\n[*] Initializing Agentic Loop...")

    # 3. Run the Agent Asynchronously
    try:
        # The Runner handles the back-and-forth loop between DeepHat's thoughts and Kali's terminal
        result = await Runner.run(agent, input=mission_trigger)
        print("\n[*] Mission Complete. Final Output:")
        print(result.final_output)
    except Exception as e:
        print(f"\n[-] Agent loop terminated unexpectedly: {e}")


if __name__ == "__main__":
    # Execute the async loop
    asyncio.run(main())