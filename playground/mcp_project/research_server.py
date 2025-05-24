from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn
import json

app = FastAPI(title="MCP Research Server")

class ResearchRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None

@app.get("/")
async def root():
    return {"status": "MCP Research Server is running"}

@app.post("/research")
async def research(request: ResearchRequest):
    try:
        # Add your research logic here
        response = {
            "query": request.query,
            "context": request.context,
            "status": "success"
        }
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    print("Starting MCP Research Server...")
    uvicorn.run(app, host="127.0.0.1", port=6274)
