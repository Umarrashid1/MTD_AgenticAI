import os
import asyncio
from openai import AsyncOpenAI
# Correct imports based on the CAI SDK structure
from cai.sdk.agents import Agent, Runner, OpenAIChatCompletionsModel
from cai.tools.reconnaissance.generic_linux_command import generic_linux_command

# Configuration for Ollama
os.environ["OPENAI_API_BASE"] = "http://172.17.0.1:11434/v1"
os.environ["OPENAI_API_KEY"] = "sk-dummy-key-not-used"
os.environ["CAI_MODEL"] = "ollama/DeepHat/DeepHat-V1-7B:latest"


async def main():
    # Setup the local client pointing to Ollama
    client = AsyncOpenAI(
        base_url=os.environ["OPENAI_API_BASE"],
        api_key=os.environ["OPENAI_API_KEY"]
    )

    agent = Agent(
        name="DeepHat_Network_Mapper",
        instructions="""You are a penetration testing agent. 
        Your goal is to map the 10.0.0.0/24 network.
        Use 'generic_linux_command' to run nmap and ip commands.
        Find live hosts and open ports, then summarize the network topology.""",
        tools=[generic_linux_command],
        model=OpenAIChatCompletionsModel(
            model=os.environ["CAI_MODEL"],
            openai_client=client,
        )
    )

    mission_trigger = "Scan the subnet 10.0.0.0/24 and tell me what is alive."

    print("[*] Starting Agentic Reconnaissance...")
    try:
        result = await Runner.run(agent, input=mission_trigger)
        print("\n[*] Mission Complete. Final Output:")
        print(result.final_output)
    except Exception as e:
        print(f"\n[-] Error during execution: {e}")


if __name__ == "__main__":
    asyncio.run(main())