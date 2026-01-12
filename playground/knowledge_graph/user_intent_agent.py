# Import necessary libraries
import os
import asyncio
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm # For OpenAI support
from google.adk.tools import ToolContext
from neo4j import GraphDatabase
from google.adk.runners import Runner
from typing import Optional, Dict, Any
from google.adk.sessions import InMemorySessionService
from google.genai import types # For creating message Content/Parts

# Convenience libraries for working with Neo4j inside of Google ADK
#from neo4j_for_adk import graphdb, tool_success, tool_error

# Define helper functions for tool responses
def tool_success(key: str, data: Any) -> dict:
    """Return a successful tool response."""
    return {
        "status": "success",
        "key": key,
        "data": data
    }

def tool_error(message: str) -> dict:
    """Return an error tool response."""
    return {
        "status": "error",
        "error_message": message
    }

import warnings
# Ignore all warnings
warnings.filterwarnings("ignore")

import logging
logging.basicConfig(level=logging.CRITICAL)


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


# --- Define Model Constants for easier use ---
MODEL_GPT_4O = "openai/gpt-4o"

llm = LiteLlm(model=MODEL_GPT_4O)

# Test LLM with a direct call
# print(llm.llm_client.completion(model=llm.model, messages=[{"role": "user", "content": "Are you ready?"}], tools=[]))

print("\nOpenAI is ready!")

# define the role and goal for the user intent agent
agent_role_and_goal = """
    You are an expert at knowledge graph use cases. 
    Your primary goal is to help the user come up with a knowledge graph use case.
"""

# give the agent some hints about what to say
agent_conversational_hints = """
    If the user is unsure what to do, make some suggestions based on classic use cases like:
    - social network involving friends, family, or professional relationships
    - logistics network with suppliers, customers, and partners
    - recommendation system with customers, products, and purchase patterns
    - fraud detection over multiple accounts with suspicious patterns of transactions
    - pop-culture graphs with movies, books, or music
"""

# describe what the output should look like
agent_output_definition = """
    A user goal has two components:
    - kind_of_graph: at most 3 words describing the graph, for example "social network" or "USA freight logistics"
    - description: a few sentences about the intention of the graph, for example "A dynamic routing and delivery system for cargo." or "Analysis of product dependencies and supplier alternatives."
"""

# specify the steps the agent should follow
agent_chain_of_thought_directions = """
    Think carefully and collaborate with the user:
    1. Understand the user's goal, which is a kind_of_graph with description
    2. Ask clarifying questions as needed
    3. When you think you understand their goal, use the 'set_perceived_user_goal' tool to record your perception
    4. Present the perceived user goal to the user for confirmation
    5. If the user agrees, use the 'approve_perceived_user_goal' tool to approve the user goal. This will save the goal in state under the 'approved_user_goal' key.
"""


# combine all the instruction components into one complete instruction...
complete_agent_instruction = f"""
{agent_role_and_goal}
{agent_conversational_hints}
{agent_output_definition}
{agent_chain_of_thought_directions}
"""

# Tool: Set Perceived User Goal
# to encourage collaboration with the user, the first tool only sets the perceived user goal

PERCEIVED_USER_GOAL = "perceived_user_goal"

def set_perceived_user_goal(kind_of_graph: str, graph_description:str, tool_context: ToolContext):
    """Sets the perceived user's goal, including the kind of graph and its description.
    
    Args:
        kind_of_graph: 2-3 word definition of the kind of graph, for example "recent US patents"
        graph_description: a single paragraph description of the graph, summarizing the user's intent
    """
    user_goal_data = {"kind_of_graph": kind_of_graph, "graph_description": graph_description}
    tool_context.state[PERCEIVED_USER_GOAL] = user_goal_data
    return tool_success(PERCEIVED_USER_GOAL, user_goal_data)

# Tool: Approve the perceived user goal
# approval from the user should trigger a call to this tool

APPROVED_USER_GOAL = "approved_user_goal"

def approve_perceived_user_goal(tool_context: ToolContext):
    """Upon approval from user, will record the perceived user goal as the approved user goal.
    
    Only call this tool if the user has explicitly approved the perceived user goal.
    """
    # Trust, but verify. 
    # Require that the perceived goal was set before approving it. 
    # Notice the tool error helps the agent take
    if PERCEIVED_USER_GOAL not in tool_context.state:
        return tool_error("perceived_user_goal not set. Set perceived user goal first, or ask clarifying questions if you are unsure.")
    
    tool_context.state[APPROVED_USER_GOAL] = tool_context.state[PERCEIVED_USER_GOAL]

    return tool_success(APPROVED_USER_GOAL, tool_context.state[APPROVED_USER_GOAL])

# add the tools to a list
user_intent_agent_tools = [set_perceived_user_goal, approve_perceived_user_goal]

# Finally, construct the agent

user_intent_agent = Agent(
    name="user_intent_agent_v1", # a unique, versioned name
    model=llm, # defined earlier in a variable
    description="Helps the user ideate on a knowledge graph use case.", # used for delegation
    instruction=complete_agent_instruction, # the complete instructions you composed earlier
    tools=user_intent_agent_tools, # the list of tools
)

print(f"Agent '{user_intent_agent.name}' created.")




# We need an async function to await for each conversation
async def run_conversation():
    user_intent_caller = await make_agent_caller(user_intent_agent)
    session_start = await user_intent_caller.get_session()
    print(f"Session Start: {session_start.state}") # expect this to be empty
    # start things off by describing your goal
    await user_intent_caller.call("""I'd like a bill of materials graph (BOM graph) which includes all levels from suppliers to finished product, 
    which can support root-cause analysis.""") 

    if PERCEIVED_USER_GOAL not in session_start.state:
        # the LLM may have asked a clarifying question. offer some more details
        await user_intent_caller.call("""I'm concerned about possible manufacturing or supplier issues.""")        

    # Optimistically presume approval.
    await user_intent_caller.call("Approve that goal.", True)

# asyncio.run(run_conversation())

#session_end = await user_intent_caller.get_session()