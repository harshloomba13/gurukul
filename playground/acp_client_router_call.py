import asyncio 
import nest_asyncio
nest_asyncio.apply()
from acp_sdk.client import Client
from smolagents import LiteLLMModel
from fastacp import AgentCollection, ACPCallingAgent
from colorama import Fore

model = LiteLLMModel(
    model_id="openai/gpt-4"
)

async def run_hospital_workflow() -> None:
    async with Client(base_url="http://localhost:8001") as insurer, Client(base_url="http://localhost:8000") as hospital:
        # agents discovery
        agent_collection = await AgentCollection.from_acp(insurer, hospital)  
        acp_agents = {agent.name: {'agent':agent, 'client':client} for client, agent in agent_collection.agents}
        print(acp_agents) 
        # passing the agents as tools to ACPCallingAgent
        acpagent = ACPCallingAgent(acp_agents=acp_agents, model=model)
        # running the agent with a user query
        result = await acpagent.run("do i need rehabilitation after a shoulder reconstruction and what is the waiting period from my insurance?")
        print(Fore.YELLOW + f"Final result: {result}" + Fore.RESET)

asyncio.run(run_hospital_workflow())