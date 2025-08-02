from collections.abc import AsyncGenerator
from acp_sdk.models import Message, MessagePart
from acp_sdk.server import RunYield, RunYieldResume, Server

from crewai import Crew, Task, Agent, LLM
from crewai_tools import RagTool

import nest_asyncio
nest_asyncio.apply()

import logging
import traceback

# Set up detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
)
logger = logging.getLogger(__name__)

server = Server()
llm = LLM(model="openai/gpt-4", max_tokens=1024)

config = {
    "llm": {
        "provider": "openai",
        "config": {
            "model": "gpt-4",
        }
    },
    "embedding_model": {
        "provider": "openai",
        "config": {
            "model": "text-embedding-ada-002"
        }
    }
}
rag_tool = RagTool(config=config,  
                   chunk_size=1200,       
                   chunk_overlap=200,     
                  )
rag_tool.add("./data/gold-hospital-and-premium-extras.pdf", data_type="pdf_file")


@server.agent()
async def policy_agent(input: list[Message]) -> AsyncGenerator[RunYield, RunYieldResume]:
    logger.info("policy_agent called with input: %s", input)
    try:
        "This is an agent for questions around policy coverage, it uses a RAG pattern to find answers based on policy documentation. Use it to help answer questions on coverage and waiting periods."

        insurance_agent = Agent(
            role="Senior Insurance Coverage Assistant", 
            goal="Determine whether something is covered or not",
            backstory="You are an expert insurance agent designed to assist with coverage queries",
            verbose=True,
            allow_delegation=False,
            llm=llm,
            tools=[rag_tool], 
            max_retry_limit=5
        )
        logger.info("Agent created: %s", insurance_agent)
        task1 = Task(
             description=input[0].parts[0].content,
             expected_output = "A comprehensive response as to the users question",
             agent=insurance_agent
        )
        logger.info("Task created: %s", task1)
        crew = Crew(agents=[insurance_agent], tasks=[task1], verbose=True)
        logger.info("Crew created: %s", crew)
        task_output = await crew.kickoff_async()
        logger.info("Task output: %s", task_output)
        yield Message(parts=[MessagePart(content=str(task_output))])
    except Exception as e:
        logger.error("Exception in policy_agent: %s", e)
        logger.error(traceback.format_exc())
        yield Message(parts=[MessagePart(content=f"❌ Error: {str(e)}\n{traceback.format_exc()} ")])

if __name__ == "__main__":
    server.run(port=8001)