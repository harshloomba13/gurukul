
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import uuid
import datetime

app = FastAPI()

# --- Mock Store (simulate MCP server memory layer) ---
EVENT_DB = {}
CONTENT_DB = {}
POSTED_CHANNELS = []

# --- Models ---
class Event(BaseModel):
    title: str
    date: str
    menu: List[str]
    price: int
    features: List[str]

class EventResponse(BaseModel):
    event_id: str
    status: str
    message: str

# --- Agents (Simplified Functions) ---
def planner_agent(event: Event) -> str:
    event_id = str(uuid.uuid4())
    EVENT_DB[event_id] = {
        "metadata": event.dict(),
        "created_at": datetime.datetime.utcnow().isoformat(),
        "status": "planned"
    }
    return event_id

def content_creator_agent(event: Event) -> str:
    return f"🎉 {event.title} on {event.date}! Enjoy {', '.join(event.menu)} with {', '.join(event.features)}. Price: ₹{event.price}. Book now!"

def distribution_agent(event_id: str, content: str) -> None:
    POSTED_CHANNELS.extend([
        f"Instagram: {content}",
        f"WhatsApp: {content}",
        f"Guest Portal: {content}"
    ])
    EVENT_DB[event_id]["status"] = "promoted"

# --- API Endpoint ---
@app.post("/create-event", response_model=EventResponse)
def create_event(event: Event):
    try:
        event_id = planner_agent(event)
        content = content_creator_agent(event)
        CONTENT_DB[event_id] = content
        distribution_agent(event_id, content)
        return EventResponse(event_id=event_id, status="success", message="Event created and promoted.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
