import os
import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv

# 1. Standard SDK imports
from cai.sdk.agents import Agent, Runner, OpenAIChatCompletionsModel

# 2. Import the actual function (ensure the path matches where you saved the nmap code)
# If it's in a file named nmap_tool.py, it would be: from nmap_tool import nmap
from cai.tools.reconnaissance.nmap import nmap

load_dotenv()

async def main():
    # 3. Setup the Model (Required for the agent to function)
    model_config = OpenAIChatCompletionsModel(
        model=os.getenv('CAI_MODEL', "openai/gpt-4o"),
        openai_client=AsyncOpenAI(),
    )

    # 4. Define the Agent
    agent = Agent(
        name="DeepHat_Scanner",
        instructions="""You are a network mapping agent.
        Use your nmap tool to discover hosts on 10.0.0.0/24.
        Output a clean list of active IPs and open ports.""",
        tools=[nmap], # Pass the function reference directly
        model=model_config
    )

    mission_trigger = "Scan the 10.0.0.0/24 subnet and map the network."

    try:
        # 5. Execute using the Runner
        result = await Runner.run(agent, input=mission_trigger)
        print(f"\n[*] Scan Result:\n{result.final_output}")
    except Exception as e:
        print(f"\n[-] Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())