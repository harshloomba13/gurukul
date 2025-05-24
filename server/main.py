from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from langgraph.graph import invoke_graph
from mcp_client import MCP_ChatBot
import os

# Debug print to show environment variables
print("\n=== Environment Variables Debug ===")
print("Current working directory:", os.getcwd())
print("\nAll environment variables:")
for key, value in os.environ.items():
    if 'API' in key or 'KEY' in key:  # Only show API keys and similar sensitive variables
        print(f"{key}: {'*' * len(value)}")  # Mask the actual values
    else:
        print(f"{key}: {value}")
print("=== End Environment Variables Debug ===\n")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    message: str

@app.post("/agent")
def route_to_agent(msg: Message):
    response = invoke_graph(msg.message)
    return {"response": response}

@app.get("/")
async def health_check():
    chatbot = MCP_ChatBot()
    await chatbot.connect_to_servers()  # Just connect, don't run chat loop
    return {"message": "Madhushala backend is running"}
