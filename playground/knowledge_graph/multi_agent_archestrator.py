# Import necessary libraries
import os
import asyncio
import warnings
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm # For OpenAI support
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types # For creating message Content/Parts
from typing import Optional, Dict, Any
# Standard Neo4j driver
from neo4j import GraphDatabase
from google.adk.tools.tool_context import ToolContext
from tool import get_approved_user_goal

warnings.filterwarnings("ignore")

import logging
logging.basicConfig(level=logging.CRITICAL)

print("Libraries imported.")

# Define Model Constants for easier use 
MODEL_GPT = "openai/gpt-4o"

llm = LiteLlm(model=MODEL_GPT)

# Test LLM with a direct call
print(llm.llm_client.completion(model=llm.model, 
                                messages=[{"role": "user", 
                                           "content": "Are you ready?"}], 
                                tools=[]))

print("\nOpenAI is ready for use.")

# Connect to Neo4j database
# Note: You'll need to set up a Neo4j database and provide connection details
# For now, we'll create a mock connection to avoid errors
try:
    # This would be the actual connection code:
    # driver = GraphDatabase.driver("bolt://localhost:7687", auth=("username", "password"))
    # with driver.session() as session:
    #     result = session.run("RETURN 'Neo4j is Ready!' as message")
    #     neo4j_is_ready = result.single()["message"]
    
    # Mock response for now
    neo4j_is_ready = "Neo4j connection would be ready (mock response)"
    print("Neo4j driver imported successfully")
except Exception as e:
    print(f"Neo4j connection error: {e}")
    neo4j_is_ready = "Neo4j connection failed"

print(neo4j_is_ready)

# Create a mock graphdb object for the functions
class MockGraphDB:
    def send_query(self, query, params=None):
        return {
            "status": "success",
            "query_result": [{"reply": f"Hello to you, {params.get('person_name', 'Unknown')} (mock response)"}]
        }

graphdb = MockGraphDB()

# Define a basic tool -- send a parameterized cypher query
def say_hello(person_name: str) -> dict:
    """Formats a welcome message to a named person. 

    Args:
        person_name (str): the name of the person saying hello

    Returns:
        dict: A dictionary containing the results of the query.
              Includes a 'status' key ('success' or 'error').
              If 'success', includes a 'query_result' key with an array of result rows.
              If 'error', includes an 'error_message' key.
    """
    return graphdb.send_query("RETURN 'Hello to you, ' + $person_name AS reply",
    {
        "person_name": person_name
    })


# Example tool usage (optional test)
#print(say_hello("ABK"))
# Example tool usage (optional test)
#print(say_hello("RETURN 'injection attack avoided'"))

def say_hello_stateful(user_name:str, tool_context:ToolContext):
    """Says hello to the user, recording their name into state.
    
    Args:
        user_name (str): The name of the user.
    """
    tool_context.state["user_name"] = user_name
    print("\ntool_context.state['user_name']:", tool_context.state["user_name"])
    return graphdb.send_query(
        f"RETURN 'Hello to you, ' + $user_name + '.' AS reply",
    {
        "user_name": user_name
    })

# Define the new goodbye tool
def say_goodbye(person_name: str) -> dict:
    """Provides a simple farewell message to conclude the conversation."""
    return graphdb.send_query("RETURN 'Goodbye from Cypher!' as farewell",{
        "person_name": person_name
    })

def say_goodbye_stateful(tool_context: ToolContext) -> dict:
    """Says goodbye to the user, reading their name from state."""
    user_name = tool_context.state.get("user_name", "stranger")
    print("\ntool_context.state['user_name']:", user_name)
    return graphdb.send_query("RETURN 'Goodbye, ' + $user_name + ', nice to chat with you!' AS reply",
    {
        "user_name": user_name
    })


print("✅ State-aware 'say_hello_stateful' and 'say_goodbye_stateful' tools defined.")


# Define the Cypher Agent
hello_agent = Agent(
    name="hello_agent_v1",
    model=llm, # defined earlier in a variable
    description="Has friendly chats with a user.",
    instruction="""You are a helpful assistant, chatting with a user. 
                Be polite and friendly, introducing yourself and asking who the user is. 

                If the user provides their name, use the 'say_hello' tool to get a custom greeting.
                If the tool returns an error, inform the user politely. 
                If the tool is successful, present the reply.
                """,
    tools=[say_hello], # Pass the function directly
)

print(f"Agent '{hello_agent.name}' created.")

# --- Greeting Agent ---
greeting_subagent = Agent(
    model=llm,
    name="greeting_subagent_v1",
    instruction="You are the Greeting Agent. Your ONLY task is to provide a friendly greeting to the user. "
                "Use the 'say_hello' tool to generate the greeting. "
                "If the user provides their name, make sure to pass it to the tool. "
                "Do not engage in any other conversation or tasks.",
    description="Handles simple greetings and hellos using the 'say_hello' tool.", # Crucial for delegation
    tools=[say_hello],
)
print(f"✅ Agent '{greeting_subagent.name}' created.")

# define a stateful greeting agent. the only difference is that this agent will use the stateful say_hello_stateful tool
greeting_agent_stateful = Agent(
    model=llm,
    name="greeting_agent_stateful_v1",
    instruction="You are the Greeting Agent. Your ONLY task is to provide a friendly greeting using the 'say_hello' tool. Do nothing else.",
    description="Handles simple greetings and hellos using the 'say_hello_stateful' tool.",
    tools=[say_hello_stateful],
)
print(f"✅ Agent '{greeting_agent_stateful.name}' redefined.")


# --- Farewell Agent ---
farewell_subagent = Agent(
    # Can use the same or a different model
    model=llm, # Sticking with GPT for this example
    name="farewell_subagent_v1",
    instruction="You are the Farewell Agent. Your ONLY task is to provide a polite goodbye message. "
                "Use the 'say_goodbye' tool when the user indicates they are leaving or ending the conversation "
                "(e.g., using words like 'bye', 'goodbye', 'thanks bye', 'see you'). "
                "Do not perform any other actions.",
    description="Handles simple farewells and goodbyes using the 'say_goodbye' tool.", # Crucial for delegation
    tools=[say_goodbye],
)
print(f"✅ Agent '{farewell_subagent.name}' created.")

farewell_agent_stateful = Agent(
    model=llm,
    name="farewell_agent_stateful_v1",
    instruction="You are the Farewell Agent. Your ONLY task is to provide a polite goodbye message using the 'say_goodbye_stateful' tool. Do not perform any other actions.",
    description="Handles simple farewells and goodbyes using the 'say_goodbye_stateful' tool.",
    tools=[say_goodbye_stateful],
)
print(f"✅ Agent '{farewell_agent_stateful.name}' redefined.")

root_agent = Agent(
    name="friendly_agent_team_v1", # Give it a new version name
    model=llm,
    description="The main coordinator agent. Delegates greetings/farewells to specialists.",
    instruction="""You are the main Agent coordinating a team. Your primary responsibility is to be friendly.
 
                You have specialized sub-agents: 
                1. 'greeting_agent': Handles simple greetings like 'Hi', 'Hello'. Delegate to it for these. 
                2. 'farewell_agent': Handles simple farewells like 'Bye', 'See you'. Delegate to it for these. 

                Analyze the user's query. If it's a greeting, delegate to 'greeting_agent'. 
                If it's a farewell, delegate to 'farewell_agent'. 
                
                For anything else, respond appropriately or state you cannot handle it.
                """,
    tools=[], # No tools for the root agent
    # Key change: Link the sub-agents here!
    sub_agents=[greeting_subagent, farewell_subagent]
)


print(f"✅ Root Agent '{root_agent.name}' created with sub-agents: {[sa.name for sa in root_agent.sub_agents]}")


root_agent_stateful = Agent(
    name="friendly_team_stateful", # New version name
    model=llm,
    description="The main coordinator agent. Delegates greetings/farewells to specialists.",
    instruction="""You are the main Agent coordinating a team. Your primary responsibility is to be friendly.

                You have specialized sub-agents: 
                1. 'greeting_agent_stateful': Handles simple greetings like 'Hi', 'Hello'. Delegate to it for these. 
                2. 'farewell_agent_stateful': Handles simple farewells like 'Bye', 'See you'. Delegate to it for these. 

                Analyze the user's query. If it's a greeting, delegate to 'greeting_agent_stateful'. If it's a farewell, delegate to 'farewell_agent_stateful'. 
                
                For anything else, respond appropriately or state you cannot handle it.
                """,
        tools=[], # Still no tools for root
        sub_agents=[greeting_agent_stateful, farewell_agent_stateful], # Include sub-agents
    )

print(f"✅ Root Agent '{root_agent_stateful.name}' created using agents with stateful tools.")

class AgentCaller:
    """A simple wrapper class for interacting with an ADK agent."""
    
    def __init__(self, agent: Agent, runner: Runner, 
                 user_id: str, session_id: str):
        """Initialize the AgentCaller with required components."""
        self.agent = agent
        self.runner = runner
        self.user_id = user_id
        self.session_id = session_id


    def get_session(self):
        return self.runner.session_service.get_session(app_name=self.runner.app_name, user_id=self.user_id, session_id=self.session_id)

    
    async def call(self, user_message: str, verbose: bool = False):
        """Call the agent with a query and return the response."""
        print(f"\n>>> User Message: {user_message}")

        # Prepare the user's message in ADK format
        content = types.Content(role='user', parts=[types.Part(text=user_message)])

        final_response_text = "Agent did not produce a final response." 
        
        # Key Concept: run_async executes the agent logic and yields Events.
        # We iterate through events to find the final answer.
        async for event in self.runner.run_async(user_id=self.user_id, session_id=self.session_id, new_message=content):
            # You can uncomment the line below to see *all* events during execution
            if verbose:
                print(f"  [Event] Author: {event.author}, Type: {type(event).__name__}, Final: {event.is_final_response()}, Content: {event.content}")

            # Key Concept: is_final_response() marks the concluding message for the turn.
            if event.is_final_response():
                if event.content and event.content.parts:
                    # Assuming text response in the first part
                    final_response_text = event.content.parts[0].text
                elif event.actions and event.actions.escalate: # Handle potential errors/escalations
                    final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
                break # Stop processing events once the final response is found

        print(f"<<< Agent Response: {final_response_text}")
        return final_response_text


async def make_agent_caller(agent: Agent, initial_state: Optional[Dict[str, Any]] = {}) -> AgentCaller:
    """Create and return an AgentCaller instance for the given agent."""
    app_name = agent.name + "_app"
    user_id = agent.name + "_user"
    session_id = agent.name + "_session_01"
    
    # Initialize a session service and a session
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state=initial_state
    )
    
    runner = Runner(
        agent=agent,
        app_name=app_name,
        session_service=session_service
    )
    
    return AgentCaller(agent, runner, user_id, session_id)

# We need an async function to await our interaction helper
async def run_conversation():
    #hello_agent_caller = await make_agent_caller(hello_agent)
    #await hello_agent_caller.call("Hello I'm ABK")
    #await hello_agent_caller.call("I am excited")
    root_agent_caller = await make_agent_caller(root_agent)
    await root_agent_caller.call("Hello I'm ABK", True)
    await root_agent_caller.call("Thanks, bye!", True)
# Execute the conversation using asyncio

#asyncio.run(run_conversation())

async def run_stateful_conversation():
    #hello_agent_caller = await make_agent_caller(hello_agent)
    #await hello_agent_caller.call("Hello I'm ABK")
    #await hello_agent_caller.call("I am excited")
    root_stateful_caller = await make_agent_caller(root_agent_stateful)
    session = await root_stateful_caller.get_session()
    print(f"Initial State: {session.state}")
    await root_stateful_caller.call("Hello I'm ABK", True)
    await root_stateful_caller.call("Thanks, bye!", True)
    # Execute the conversation using await in an async context (like Colab/Jupyter)

#asyncio.run(run_stateful_conversation())


async def run_interactive_conversation():
    root_stateful_caller = await make_agent_caller(root_agent_stateful)
    
    while True:
        user_query = input("Ask me something (or type 'exit' to quit): ")
        if user_query.lower() == 'exit':
            break
        response = await root_stateful_caller.call(user_query)
        print(f"Response: {response}")

# Execute the interactive conversation
asyncio.run(run_interactive_conversation())