from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from local_graph.graph import invoke_graph
import os
import logging
logging.basicConfig(level=logging.INFO)

# Debug print to show environment variables
logging.info("\n=== Environment Variables Debug ===")
logging.info("Current working directory:", os.getcwd())
logging.info("\nAll environment variables:")
for key, value in os.environ.items():
    if 'API' in key or 'KEY' in key:  # Only show API keys and similar sensitive variables
        logging.info(f"{key}: {'*' * len(value)}")  # Mask the actual values
    else:
        logging.info(f"{key}: {value}")
logging.info("=== End Environment Variables Debug ===\n")

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
async def route_to_agent(msg: Message):
    logging.info(f"Received message: {msg.message}")
    response = await invoke_graph(msg.message)
    logging.info(f"Response: {response}")
    return {"response": response}

@app.get("/")
async def health_check():
    logging.info("Madhushala backend is running")
    return {"message": "Madhushala backend is running"}
