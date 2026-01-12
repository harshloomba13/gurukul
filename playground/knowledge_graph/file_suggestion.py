# Import necessary libraries
import os
import asyncio
from pathlib import Path

from itertools import islice
from dotenv import load_dotenv, find_dotenv
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm # For OpenAI support
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.adk.tools import ToolContext
from google.genai import types # For creating message Content/Parts
from tools import get_approved_user_goal
# For type hints
from typing import Dict, Any, List
from typing import Optional, Dict, Any
import warnings
# Ignore all warnings
warnings.filterwarnings("ignore")

import logging
logging.basicConfig(level=logging.CRITICAL)

print("Libraries imported.")

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
    
def load_env():
    _ = load_dotenv(find_dotenv())

def get_neo4j_import_dir():
    """Gets the neo4j import directory from an environment variable
    """
    load_env()
    neo4j_import_dir = os.getenv("NEO4J_IMPORT_DIR")
    return neo4j_import_dir

# --- Define Model Constants for easier use ---
MODEL_GPT_4O = "openai/gpt-4o"

llm = LiteLlm(model=MODEL_GPT_4O)

# Test LLM with a direct call
print(llm.llm_client.completion(model=llm.model, messages=[{"role": "user", "content": "Are you ready?"}], tools=[]))

print("\nOpenAI is ready.")

file_suggestion_agent_instruction = """
You are a constructive critic AI reviewing a list of files. Your goal is to suggest relevant files
for constructing a knowledge graph.

**Task:**
Review the file list for relevance to the kind of graph and description specified in the approved user goal. 

For any file that you're not sure about, use the 'sample_file' tool to get 
a better understanding of the file contents. 

Only consider structured data files like CSV or JSON.

Prepare for the task:
- use the 'get_approved_user_goal' tool to get the approved user goal

Think carefully, repeating these steps until finished:
1. list available files using the 'list_available_files' tool
2. evaluate the relevance of each file, then record the list of suggested files using the 'set_suggested_files' tool
3. use the 'get_suggested_files' tool to get the list of suggested files
4. ask the user to approve the set of suggested files
5. If the user has feedback, go back to step 1 with that feedback in mind
6. If approved, use the 'approve_suggested_files' tool to record the approval
"""

# Tool: List Import Files

# this constant will be used as the key for storing the file list in the tool context state
ALL_AVAILABLE_FILES = "all_available_files"

def list_available_files(tool_context:ToolContext) -> dict:
    f"""Lists files available for knowledge graph construction.
    All files are relative to the import directory.

    Returns:
        dict: A dictionary containing metadata about the content.
                Includes a 'status' key ('success' or 'error').
                If 'success', includes a {ALL_AVAILABLE_FILES} key with list of file names.
                If 'error', includes an 'error_message' key.
                The 'error_message' may have instructions about how to handle the error.
    ""=]]]]]]]]]
    WQa`cd
    # get the import dir using the helper function
    import_dir = Path(get_neo4j_import_dir())

    # get a list of relative file names, so files must be rooted at the import dir
    file_names = [str(x.relative_to(import_dir)) 
                 for x in import_dir.rglob("*") 
                 if x.is_file()]

    # save the list to state so we can inspect it later
    tool_context.state[ALL_AVAILABLE_FILES] = file_names

    return tool_success(ALL_AVAILABLE_FILES, file_names)


# Tool: Sample File
# This is a simple file reading tool that only works on files from the import directory
def sample_file(file_path: str, tool_context: ToolContext) -> dict:
    """Samples a file by reading its content as text.
    
    Treats any file as text and reads up to a maximum of 100 lines.
    
    Args:
      file_path: file to sample, relative to the import directory
      
    Returns:
        dict: A dictionary containing metadata about the content,
            along with a sampling of the file.
            Includes a 'status' key ('success' or 'error').
            If 'success', includes a 'content' key with textual file content.
            If 'error', includes an 'error_message' key.
            The 'error_message' may have instructions about how to handle the error.
    """
    # Trust, but verify. The agent may invent absolute file paths. 
    if Path(file_path).is_absolute():
        return tool_error("File path must be relative to the import directory. Make sure the file is from the list of available files.")
    
    import_dir = Path(get_neo4j_import_dir())

    # create the full path by extending from the import_dir
    full_path_to_file = import_dir / file_path
    
    # of course, _that_ may not exist
    if not full_path_to_file.exists():
        return tool_error(f"File does not exist in import directory. Make sure {file_path} is from the list of available files.")
    
    try:
        # Treat all files as text
        with open(full_path_to_file, 'r', encoding='utf-8') as file:
            # Read up to 100 lines
            lines = list(islice(file, 100))
            content = ''.join(lines)
            return tool_success("content", content)
    
    except Exception as e:
        return tool_error(f"Error reading or processing file {file_path}: {e}")


# Tool: Set/Get suggested files
SUGGESTED_FILES = "suggested_files"

def set_suggested_files(suggest_files:List[str], tool_context:ToolContext) -> Dict[str, Any]:
    """Set the suggested files to be used for data import.

    Args:
        suggest_files (List[str]): List of file paths to suggest

    Returns:
        Dict[str, Any]: A dictionary containing metadata about the content.
                Includes a 'status' key ('success' or 'error').
                If 'success', includes a {SUGGESTED_FILES} key with list of file names.
                If 'error', includes an 'error_message' key.
                The 'error_message' may have instructions about how to handle the error.
    """
    tool_context.state[SUGGESTED_FILES] = suggest_files
    return tool_success(SUGGESTED_FILES, suggest_files)

# Helps encourage the LLM to first set the suggested files.
# This is an important strategy for maintaining consistency through defined values.
def get_suggested_files(tool_context:ToolContext) -> Dict[str, Any]:
    """Get the files to be used for data import.

    Returns:
        Dict[str, Any]: A dictionary containing metadata about the content.
                Includes a 'status' key ('success' or 'error').
                If 'success', includes a {SUGGESTED_FILES} key with list of file names.
                If 'error', includes an 'error_message' key.
    """
    if SUGGESTED_FILES not in tool_context.state:
        return tool_error("No suggested files have been set yet. Please use the 'set_suggested_files' tool first.")
    
    return tool_success(SUGGESTED_FILES, tool_context.state[SUGGESTED_FILES])

# Tool: Approve Suggested Files
# Just like the previous lesson, you'll define a tool which
# accepts no arguments and can sanity check before approving.
APPROVED_FILES = "approved_files"

def approve_suggested_files(tool_context:ToolContext) -> Dict[str, Any]:
    """Approves the {SUGGESTED_FILES} in state for further processing as {APPROVED_FILES}.
    
    If {SUGGESTED_FILES} is not in state, return an error.
    """
    if SUGGESTED_FILES not in tool_context.state:
        return tool_error("Current files have not been set. Take no action other than to inform user.")

    tool_context.state[APPROVED_FILES] = tool_context.state[SUGGESTED_FILES]
    return tool_success(APPROVED_FILES, tool_context.state[APPROVED_FILES])


    # List of tools for the file suggestion agent
file_suggestion_agent_tools = [get_approved_user_goal, list_available_files, sample_file, 
    set_suggested_files, get_suggested_files,
    approve_suggested_files
]


# Finally, construct the agent

file_suggestion_agent = Agent(
    name="file_suggestion_agent_v1",
    model=llm, # defined earlier in a variable
    description="Helps the user select files to import.",
    instruction=file_suggestion_agent_instruction,
    tools=file_suggestion_agent_tools,
)

print(f"Agent '{file_suggestion_agent.name}' created.")

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


async def run_conversation():
    file_suggestion_caller = await make_agent_caller(file_suggestion_agent, {
        "approved_user_goal": {
            "kind_of_graph": "supply chain analysis",
            "description": "A multi-level bill of materials for manufactured products, useful for root cause analysis.."
        }   
    })
    await file_suggestion_caller.call("What files can we use for import?")

    session_end = await file_suggestion_caller.get_session()

    print("\n---\n")

    # expect that the agent has listed available files
    if ALL_AVAILABLE_FILES in session_end.state:
        print("Available files: ", session_end.state[ALL_AVAILABLE_FILES])
    else:
        print("Available files: Not set yet")

    # the suggested files should be reasonable looking CSV files
    if SUGGESTED_FILES in session_end.state:
        print("Suggested files: ", session_end.state[SUGGESTED_FILES])
    else:
        print("Suggested files: Not set yet")

    # Agree with the file suggestions
    await file_suggestion_caller.call("Yes, let's do it")

    session_end = await file_suggestion_caller.get_session()

    print("\n---\n")

    if APPROVED_FILES in session_end.state:
        print("Approved files: ", session_end.state[APPROVED_FILES])
    else:
        print("Approved files: Not set yet")

asyncio.run(run_conversation())