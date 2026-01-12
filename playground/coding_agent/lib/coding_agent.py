"""Coding agent implementation."""

from typing import List, Dict, Any, Callable, Optional
import json
import sys
import os
from .logger import logger

# Handle import of llm module from parent directory
try:
    from ..llm import llm
except ImportError:
    # Add parent directory to path for direct script execution
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    from llm import llm

def coding_agent(
    query: str,
    messages: List[Dict[str, str]],
    client,
    tools: Dict[str, Callable],
    tools_schemas: List[Dict],
    system: str = "You are a helpful assistant",
    sbx=None,
    **kwargs
) -> tuple[List[Dict[str, str]], Dict]:
    """
    Main coding agent function that processes queries and executes tools.
    
    Args:
        query: User query
        messages: Conversation history
        client: OpenAI client instance
        tools: Dictionary of available tools
        tools_schemas: List of tool schemas
        system: System prompt
        sbx: Sandbox instance
        **kwargs: Additional arguments
    
    Returns:
        Tuple of (updated messages, usage info)
    """
    # Add user message
    messages.append({"role": "user", "content": query})
    
    # Call LLM with tools
    try:
        # Prepare kwargs for llm function
        llm_kwargs = kwargs.copy()
        if tools_schemas:
            llm_kwargs['tools'] = tools_schemas
        
        response = llm(
            client=client,
            messages=messages,
            system=system,
            **llm_kwargs
        )
        
        # Process response - handle different response formats
        if hasattr(response, 'choices') and len(response.choices) > 0:
            assistant_message = response.choices[0].message
            content = assistant_message.content if hasattr(assistant_message, 'content') else str(assistant_message)
            
            # Check for tool calls
            if hasattr(assistant_message, 'tool_calls') and assistant_message.tool_calls:
                # Execute tool calls
                tool_results = []
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    if tool_name in tools:
                        # Execute the tool
                        if tool_name == "execute_code" and sbx is not None:
                            result = tools[tool_name](code=tool_args.get("code", ""), sbx=sbx)
                        else:
                            result = tools[tool_name](**tool_args)
                        
                        tool_results.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_name,
                            "content": str(result)
                        })
                
                # Add assistant message with tool calls
                messages.append({
                    "role": "assistant",
                    "content": content,
                    "tool_calls": [tc.model_dump() if hasattr(tc, 'model_dump') else str(tc) for tc in assistant_message.tool_calls]
                })
                
                # Add tool results
                messages.extend(tool_results)
                
                # Get final response after tool execution
                final_response = llm(
                    client=client,
                    messages=messages,
                    system=system,
                    **llm_kwargs
                )
                
                if hasattr(final_response, 'choices') and len(final_response.choices) > 0:
                    final_content = final_response.choices[0].message.content if hasattr(final_response.choices[0].message, 'content') else str(final_response.choices[0].message)
                    messages.append({"role": "assistant", "content": final_content})
                    response = final_response
                else:
                    messages.append({"role": "assistant", "content": content})
            else:
                messages.append({"role": "assistant", "content": content})
        else:
            # Fallback for other response formats
            content = str(response)
            messages.append({"role": "assistant", "content": content})
        
        # Extract usage if available
        usage = {}
        if hasattr(response, 'usage'):
            usage = {
                "prompt_tokens": getattr(response.usage, 'prompt_tokens', 0),
                "completion_tokens": getattr(response.usage, 'completion_tokens', 0),
                "total_tokens": getattr(response.usage, 'total_tokens', 0)
            }
        
        return messages, usage
        
    except Exception as e:
        logger.error(f"Error in coding_agent: {e}")
        import traceback
        logger.error(traceback.format_exc())
        error_message = f"An error occurred: {str(e)}"
        messages.append({"role": "assistant", "content": error_message})
        return messages, {}


def log(
    agent_func: Callable,
    query: str,
    messages: List[Dict[str, str]],
    client,
    tools: Dict[str, Callable],
    tools_schemas: List[Dict],
    system: str = "You are a helpful assistant",
    sbx=None,
    **kwargs
) -> tuple[List[Dict[str, str]], Dict]:
    """
    Wrapper function that logs and calls the coding agent.
    
    Args:
        agent_func: The agent function to call
        query: User query
        messages: Conversation history
        client: OpenAI client instance
        tools: Dictionary of available tools
        tools_schemas: List of tool schemas
        system: System prompt
        sbx: Sandbox instance
        **kwargs: Additional arguments
    
    Returns:
        Tuple of (updated messages, usage info)
    """
    logger.info(f"Processing query: {query}")
    return agent_func(
        query=query,
        messages=messages,
        client=client,
        tools=tools,
        tools_schemas=tools_schemas,
        system=system,
        sbx=sbx,
        **kwargs
    )

