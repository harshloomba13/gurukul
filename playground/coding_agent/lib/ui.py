"""UI components for the coding agent."""

try:
    import gradio as gr
    GRADIO_AVAILABLE = True
except ImportError:
    GRADIO_AVAILABLE = False

from typing import List, Dict, Callable, Any
from .logger import logger

class ui:
    """Gradio-based UI for the coding agent with CLI fallback."""
    
    def __init__(
        self,
        agent_func: Callable,
        messages: List[Dict[str, str]],
        client,
        tools_schemas: List[Dict],
        system: str = "You are a helpful assistant",
        tools: Dict[str, Callable] = None,
        sbx=None,
    ):
        """
        Initialize the UI.
        
        Args:
            agent_func: The agent function to use
            messages: Initial conversation messages
            client: OpenAI client instance
            tools_schemas: List of tool schemas
            system: System prompt
            tools: Dictionary of available tools
            sbx: Sandbox instance
        """
        self.agent_func = agent_func
        self.messages = messages.copy()
        self.client = client
        self.tools_schemas = tools_schemas
        self.system = system
        self.tools = tools or {}
        self.sbx = sbx
        
        # Create Gradio interface if available, otherwise prepare for CLI fallback
        if GRADIO_AVAILABLE:
            self.interface = self._create_interface()
        else:
            self.interface = None
            logger.warning("Gradio not available. Will use CLI interface instead.")
    
    def _create_interface(self):
        """Create the Gradio interface."""
        def chat_fn(message, history):
            """Handle chat messages."""
            try:
                # Call the agent
                updated_messages, usage = self.agent_func(
                    query=message,
                    messages=self.messages,
                    client=self.client,
                    tools=self.tools,
                    tools_schemas=self.tools_schemas,
                    system=self.system,
                    sbx=self.sbx,
                )
                
                # Update messages
                self.messages = updated_messages
                
                # Get the last assistant message
                if updated_messages and updated_messages[-1].get("role") == "assistant":
                    response = updated_messages[-1].get("content", "")
                    return response
                else:
                    return "No response generated"
                    
            except Exception as e:
                logger.error(f"Error in chat_fn: {e}")
                return f"Error: {str(e)}"
        
        return gr.ChatInterface(
            fn=chat_fn,
            title="Coding Agent",
            description="Ask me to code something!",
        )
    
    def launch(self, **kwargs):
        """Launch the Gradio interface or fall back to CLI."""
        if self.interface is not None:
            return self.interface.launch(**kwargs)
        else:
            # Fallback to CLI interface
            print("=" * 60)
            print("Gradio UI not available. Using CLI interface instead.")
            print("To use the web UI, install gradio: pip install gradio")
            print("=" * 60)
            print(f"{self.system}")
            print("Type '/exit' to quit\n")
            
            while True:
                try:
                    query = input(">: ")
                    if query.strip() == "/exit":
                        print("Goodbye!")
                        break
                    
                    if not query.strip():
                        continue
                    
                    # Call the agent
                    updated_messages, usage = self.agent_func(
                        query=query,
                        messages=self.messages,
                        client=self.client,
                        tools=self.tools,
                        tools_schemas=self.tools_schemas,
                        system=self.system,
                        sbx=self.sbx,
                    )
                    
                    # Update messages
                    self.messages = updated_messages
                    
                    # Print the response
                    if updated_messages and updated_messages[-1].get("role") == "assistant":
                        response = updated_messages[-1].get("content", "")
                        print(f"\n{response}\n")
                    
                except KeyboardInterrupt:
                    print("\n\nGoodbye!")
                    break
                except Exception as e:
                    logger.error(f"Error: {e}")
                    print(f"Error: {str(e)}\n")
            
            return None

