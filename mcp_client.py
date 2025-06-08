import requests
import json

class API_ChatBot:

    def __init__(self):
        self.api_url = "https://madhushala-api.onrender.com/agent"

    async def process_query(self, query):
        system_prompt = "You are an assistant that MUST use the available tools. When a user asks for menu suggestions, event write-ups, or poetic descriptions for food/events, you MUST use the handle_writeup tool. Never generate responses directly - always use the appropriate tool."
        messages = [{'role':'user', 'content':query}]
        print("\n=== Debug: Available Tools ===")
        print(self.available_tools)
        print("=== End Available Tools ===\n")
        
        response = self.anthropic.messages.create(max_tokens = 2024,
                                      model = 'claude-3-5-sonnet-20241022', 
                                      system = system_prompt,
                                      tools = self.available_tools,
                                      messages = messages)
        process_query = True
        while process_query:
            assistant_content = []
            for content in response.content:
                if content.type =='text':
                    print(f"\n=== Debug: Text Response ===")
                    print(content.text)
                    print("=== End Text Response ===\n")
                    assistant_content.append(content)
                    if(len(response.content) == 1):
                        process_query= False
                elif content.type == 'tool_use':
                    print(f"\n=== Debug: Tool Use ===")
                    print(f"Tool Name: {content.name}")
                    print(f"Tool Args: {content.input}")
                    print("=== End Tool Use ===\n")
                    assistant_content.append(content)
                    messages.append({'role':'assistant', 'content':assistant_content})
                    tool_id = content.id
                    tool_args = content.input
                    tool_name = content.name
    
                    print(f"Calling tool {tool_name} with args {tool_args}")
                    
                    # Call a tool
                    #result = execute_tool(tool_name, tool_args): not anymore needed
                    # tool invocation through the client session
                    try:
                        result = await self.session.call_tool(tool_name, arguments=tool_args)
                        print(f"=== Debug: Tool result: {result} ===")
                    except Exception as e:
                        print(f"=== Debug: Tool call error: {str(e)} ===")
                        result = None
                    if result is not None:
                        messages.append({"role": "user", 
                                          "content": [
                                              {
                                                  "type": "tool_result",
                                                  "tool_use_id":tool_id,
                                                  "content": result.content
                                              }
                                          ]
                                        })
                    else:
                        messages.append({"role": "user", 
                                          "content": [
                                              {
                                                  "type": "tool_result",
                                                  "tool_use_id":tool_id,
                                                  "content": "Tool execution failed"
                                              }
                                          ]
                                        })
                    print(f"debugging step!!")
                    response = self.anthropic.messages.create(max_tokens = 2024,
                                      model = 'claude-3-5-sonnet-20241022',
                                      system = system_prompt,
                                      tools = self.available_tools,
                                      messages = messages) 
                    
                    if(len(response.content) == 1 and response.content[0].type == "text"):
                        process_query= False
            if len(response.content) == 1 and response.content[0].type == "text":
                return response.content[0].text
    
    
    async def chat_loop(self, messages):
        """Run an interactive chat loop"""
        print("\nMCP Chatbot Started!")
        print("Type your queries or 'quit' to exit.")
        
        try:
                if messages.lower() == 'quit':
                    return "Goodbye!"
                    
                response = await self.process_query(messages)
                return response
                    
        except Exception as e:
                print(f"\nError: {str(e)}")
    
    async def connect_to_server_and_run(self, messages):
        print("=== Debug: Starting HTTP server connection ===")
        # Connect to deployed API server
        server_url = "https://madhushala-api.onrender.com/sse"
        print(f"=== Debug: Connecting to {server_url} ===")
        async with sse_client(server_url) as (read, write):
            print("=== Debug: SSE client connected ===")
            async with ClientSession(read, write) as session:
                print("=== Debug: ClientSession created ===")
                self.session = session
                # Initialize the connection
                print("=== Debug: Initializing session ===")
                await session.initialize()
                print("=== Debug: Session initialized ===")
    
                # List available tools
                response = await session.list_tools()
                
                tools = response.tools
                print("\nConnected to server with tools:", [tool.name for tool in tools])
                print("Tool details:")
                for tool in tools:
                    print(f"  - {tool.name}: {tool.description}")
                
                self.available_tools = [{
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                } for tool in response.tools]
    
                response = await self.chat_loop(messages)
                return response

async def main():
    chatbot = MCP_ChatBot()
    messages = "Please use the handle_writeup tool to create a poetic menu for a birthday party"  # Test message to trigger handle_writeup
    response = await chatbot.connect_to_server_and_run(messages)
    print(f"Response: {response}")
  

if __name__ == "__main__":
    asyncio.run(main())