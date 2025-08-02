from collections.abc import AsyncGenerator
from acp_sdk.models import Message, MessagePart
from acp_sdk.server import Context, RunYield, RunYieldResume, Server
from smolagents import CodeAgent, DuckDuckGoSearchTool, LiteLLMModel, VisitWebpageTool
import logging 
from dotenv import load_dotenv

load_dotenv() 

server = Server()

model = LiteLLMModel(
    model_id="openai/gpt-4",  
    max_tokens=2048
)

@server.agent()
async def health_agent(input: list[Message], context: Context) -> AsyncGenerator[RunYield, RunYieldResume]:
    agent = CodeAgent(tools=[DuckDuckGoSearchTool(), VisitWebpageTool()], model=model)

    prompt = input[0].parts[0].content
    try:
        response = agent.run(prompt)
        yield Message(parts=[MessagePart(content=str(response))])
    except Exception as e:
        logging.error(f"Exception in health_agent: {e}", exc_info=True)
        yield Message(parts=[MessagePart(content=f"❌ Error: {str(e)}")])


if __name__ == "__main__":
    server.run(port=8000)