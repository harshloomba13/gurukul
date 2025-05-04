
from langchain.agents import initialize_agent, AgentType
from langchain.chat_models import ChatOpenAI
from langchain.tools import Tool
from langchain_mcp_tool import create_event_tool

llm = ChatOpenAI(temperature=0)

tools = [
    Tool.from_function(
        func=create_event_tool,
        name="CreateEvent",
        description="Use this to advertise or schedule a new Madhushala event (e.g., Sufi Night, dinner + music, etc.)."
    )
]

agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

response = agent.run("Create a Ghazal Night event on June 20 with biryani, jalebi, and shayari for ₹1800")
print("\nAgent Response:", response)
