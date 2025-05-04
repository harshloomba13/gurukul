
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from langgraph.graph import invoke_graph
from dotenv import load_dotenv

load_dotenv()
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
def health_check():
    return {"message": "Madhushala backend is running"}
