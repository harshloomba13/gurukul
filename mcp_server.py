import arxiv
import json
import os
from typing import List
from mcp.server.fastmcp import FastMCP
import asyncio
from fastapi import Request
from sse_starlette.sse import EventSourceResponse
from anthropic import Anthropic
from twilio.rest import Client as TwilioClient
from instagrapi import Client as InstaClient

# --- Configuration ---

anu_whatsapp=os.environ.get("ANU_WHATSAPP")
twilio_sid = os.environ.get("TWILIO_SID") 
twilio_token = os.environ.get("TWILIO_TOKEN")
twilio_whatsapp_number = os.environ.get("TWILIO_WHATSAPP_NUMBER")
instagram_username = os.environ.get("INSTAGRAM_USERNAME")
instagram_password = os.environ.get("INSTAGRAM_PASSWORD")

PAPER_DIR = "papers"

# Initialize FastMCP server
mcp = FastMCP("research", transport="sse")

# Add FastAPI for HTTP endpoints
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MessageRequest(BaseModel):
    message: str

@mcp.tool()
def search_papers(topic: str, max_results: int = 5) -> List[str]:
    """
    Search for papers on arXiv based on a topic and store their information.
    
    Args:
        topic: The topic to search for
        max_results: Maximum number of results to retrieve (default: 5)
        
    Returns:
        List of paper IDs found in the search
    """
    
    # Use arxiv to find the papers 
    client = arxiv.Client()

    # Search for the most relevant articles matching the queried topic
    search = arxiv.Search(
        query = topic,
        max_results = max_results,
        sort_by = arxiv.SortCriterion.Relevance
    )

    papers = client.results(search)
    
    # Create directory for this topic
    path = os.path.join(PAPER_DIR, topic.lower().replace(" ", "_"))
    os.makedirs(path, exist_ok=True)
    
    file_path = os.path.join(path, "papers_info.json")

    # Try to load existing papers info
    try:
        with open(file_path, "r") as json_file:
            papers_info = json.load(json_file)
    except (FileNotFoundError, json.JSONDecodeError):
        papers_info = {}

    # Process each paper and add to papers_info  
    paper_ids = []
    for paper in papers:
        paper_ids.append(paper.get_short_id())
        paper_info = {
            'title': paper.title,
            'authors': [author.name for author in paper.authors],
            'summary': paper.summary,
            'pdf_url': paper.pdf_url,
            'published': str(paper.published.date())
        }
        papers_info[paper.get_short_id()] = paper_info
    
    # Save updated papers_info to json file
    with open(file_path, "w") as json_file:
        json.dump(papers_info, json_file, indent=2)
    
    print(f"Results are saved in: {file_path}")
    
    return paper_ids

@mcp.tool()
def extract_info(paper_id: str) -> str:
    """
    Search for information about a specific paper across all topic directories.
    
    Args:
        paper_id: The ID of the paper to look for
        
    Returns:
        JSON string with paper information if found, error message if not found
    """
 
    for item in os.listdir(PAPER_DIR):
        item_path = os.path.join(PAPER_DIR, item)
        if os.path.isdir(item_path):
            file_path = os.path.join(item_path, "papers_info.json")
            if os.path.isfile(file_path):
                try:
                    with open(file_path, "r") as json_file:
                        papers_info = json.load(json_file)
                        if paper_id in papers_info:
                            return json.dumps(papers_info[paper_id], indent=2)
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    print(f"Error reading {file_path}: {str(e)}")
                    continue
    
    return f"There's no saved information related to paper {paper_id}."

@mcp.resource("papers://folders")
def get_available_folders() -> str:
    """
    List all available topic folders in the papers directory.
    
    This resource provides a simple list of all available topic folders.
    """
    folders = []
    
    # Get all topic directories
    if os.path.exists(PAPER_DIR):
        for topic_dir in os.listdir(PAPER_DIR):
            topic_path = os.path.join(PAPER_DIR, topic_dir)
            if os.path.isdir(topic_path):
                papers_file = os.path.join(topic_path, "papers_info.json")
                if os.path.exists(papers_file):
                    folders.append(topic_dir)
    
    # Create a simple markdown list
    content = "# Available Topics\n\n"
    if folders:
        for folder in folders:
            content += f"- {folder}\n"
        content += f"\nUse @{folder} to access papers in that topic.\n"
    else:
        content += "No topics found.\n"
    
    return content

@mcp.resource("papers://{topic}")
def get_topic_papers(topic: str) -> str:
    """
    Get detailed information about papers on a specific topic.
    
    Args:
        topic: The research topic to retrieve papers for
    """
    topic_dir = topic.lower().replace(" ", "_")
    papers_file = os.path.join(PAPER_DIR, topic_dir, "papers_info.json")
    
    if not os.path.exists(papers_file):
        return f"# No papers found for topic: {topic}\n\nTry searching for papers on this topic first."
    
    try:
        with open(papers_file, 'r') as f:
            papers_data = json.load(f)
        
        # Create markdown content with paper details
        content = f"# Papers on {topic.replace('_', ' ').title()}\n\n"
        content += f"Total papers: {len(papers_data)}\n\n"
        
        for paper_id, paper_info in papers_data.items():
            content += f"## {paper_info['title']}\n"
            content += f"- **Paper ID**: {paper_id}\n"
            content += f"- **Authors**: {', '.join(paper_info['authors'])}\n"
            content += f"- **Published**: {paper_info['published']}\n"
            content += f"- **PDF URL**: [{paper_info['pdf_url']}]({paper_info['pdf_url']})\n\n"
            content += f"### Summary\n{paper_info['summary'][:500]}...\n\n"
            content += "---\n\n"
        
        return content
    except json.JSONDecodeError:
        return f"# Error reading papers data for {topic}\n\nThe papers data file is corrupted."

@mcp.prompt()
def generate_search_prompt(topic: str, num_papers: int = 5) -> str:
    """Generate a prompt for Claude to find and discuss academic papers on a specific topic."""
    return f"""Search for {num_papers} academic papers about '{topic}' using the search_papers tool. Follow these instructions:
    1. First, search for papers using search_papers(topic='{topic}', max_results={num_papers})
    2. For each paper found, extract and organize the following information:
       - Paper title
       - Authors
       - Publication date
       - Brief summary of the key findings
       - Main contributions or innovations
       - Methodologies used
       - Relevance to the topic '{topic}'
    
    3. Provide a comprehensive summary that includes:
       - Overview of the current state of research in '{topic}'
       - Common themes and trends across the papers
       - Key research gaps or areas for future investigation
       - Most impactful or influential papers in this area
    
    4. Organize your findings in a clear, structured format with headings and bullet points for easy readability.
    
    Please present both detailed information about each paper and a high-level synthesis of the research landscape in {topic}."""  


# --- Helper functions ---
def call_gpt(prompt):
    # Replace with actual GPT call logic
    # Get API key from environment variable
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
    anthropic = Anthropic(api_key=api_key)
    messages = [{'role':'user', 'content':prompt}]
    response = anthropic.messages.create(max_tokens = 2024,
                                      model = 'claude-3-5-sonnet-20241022', 
                                      messages = messages)
    return response.content[0].text

def send_to_whatsapp(to_number, message):
    if not message or len(message.strip()) == 0:
        print("=== Debug: Empty message, skipping WhatsApp send ===")
        return
    
    # Truncate message if it's too long for WhatsApp (1600 char limit)
    if len(message) > 1500:  # Leave some buffer
        message = message[:1500] + "..."
        print(f"=== Debug: Message truncated to {len(message)} characters ===")
    
    client = TwilioClient(twilio_sid, twilio_token)
    client.messages.create(body=message, from_=twilio_whatsapp_number, to=to_number)

def post_to_instagram(caption):
    cl = InstaClient()
    cl.login(instagram_username, instagram_password)
    cl.photo_upload("image.jpeg", caption)  # Using relative path

def postprocess_and_route(tool_name, content):
    if tool_name in ["handle_booking", "handle_notification", "handle_todo_list"]:
        send_to_whatsapp(anu_whatsapp, content)
    elif tool_name == "handle_advertisement":
        post_to_instagram(content)
        #send_to_whatsapp(anu_whatsapp, content)
    elif tool_name == "handle_writeup":
        send_to_whatsapp(anu_whatsapp, content)

@mcp.tool(name="handle_advertisement", description="Create a promotional Instagram + WhatsApp post for the event.")
def handle_advertisement(msg: str) -> str:
    result = call_gpt(f"Create a promotional Instagram + WhatsApp post for this event: {msg}")
    postprocess_and_route("handle_advertisement", result)
    return result

@mcp.tool(name="handle_writeup", description="Suggest a menu and poetic write-up for the event.")
def handle_writeup(msg: str) -> str:
    print("=== Debug: Entering handle_writeup ===")
    print(f"Message received: {msg}")
    result = call_gpt(f"Suggest a menu and a poetic write-up for this event: {msg}")
    print("=== Debug: GPT response received ===")
    postprocess_and_route("handle_writeup", result)
    print("=== Debug: Exiting handle_writeup ===")
    return result


@mcp.tool(name="handle_notification", description="Write a WhatsApp reminder message to guests.")
def handle_notification(msg: str) -> str:
    result = call_gpt(f"Write a WhatsApp reminder message to guests about: {msg}")
    postprocess_and_route("handle_notification", result)
    return result

@mcp.tool(name="handle_todo_list", description="Generate a to-do list for the event organizer.")
def handle_todo_list(msg: str) -> str:
    result = call_gpt(f"Generate a checklist of things the event organizer needs to do before: {msg}")
    postprocess_and_route("handle_todo_list", result)
    return result

@mcp.tool(name="handle_booking", description="Handle event booking and reservation requests.")
def handle_booking(msg: str) -> str:
    result = call_gpt(f"Create a booking confirmation or response for: {msg}")
    postprocess_and_route("handle_booking", result)
    return result



# HTTP endpoints for cloud deployment
@app.post("/agent")
async def handle_agent_request(request: MessageRequest):
    """Handle agent requests via HTTP"""
    message = request.message.lower()
    
    try:
        if any(word in message for word in ["advertise", "advertisement", "promote", "marketing", "social media"]):
            result = handle_advertisement(request.message)
        elif any(word in message for word in ["menu", "food", "writeup", "poetic", "feast", "cuisine"]):
            result = handle_writeup(request.message)
        elif any(word in message for word in ["notify", "reminder", "guests", "whatsapp"]):
            result = handle_notification(request.message)
        elif any(word in message for word in ["todo", "checklist", "organizer", "tasks"]):
            result = handle_todo_list(request.message)
        elif any(word in message for word in ["booking", "reservation", "book"]):
            result = handle_booking(request.message)
        elif any(word in message for word in ["search", "papers", "research"]):
            # Extract topic from message - simple approach
            words = request.message.split()
            topic = " ".join(words[2:]) if len(words) > 2 else "quantum computing"
            result = search_papers(topic)
        else:
            # Default to writeup
            result = handle_writeup(request.message)
            
        return {"response": result}
    except Exception as e:
        return {"error": str(e)}

@app.get("/")
async def root():
    return {"message": "Madhushala backend is running", "endpoints": ["/health", "/debug", "/agent", "/mcp"]}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/debug")
async def debug_mcp():
    """Debug endpoint to check MCP status"""
    try:
        tools_info = "Error getting tools"
        try:
            tools = mcp.list_tools()
            tools_info = [tool.name for tool in tools] if tools else "No tools"
        except Exception as e:
            tools_info = f"Error: {str(e)}"
            
        return {
            "mcp_has_sse_app": hasattr(mcp, 'sse_app'),
            "mcp_transport": getattr(mcp, 'transport', 'unknown'),
            "mcp_methods": [method for method in dir(mcp) if not method.startswith('_')],
            "mcp_tools": tools_info,
            "status": "debug endpoint working"
        }
    except Exception as e:
        return {"error": f"Debug endpoint error: {str(e)}"}

# Remove the simple hardcoded endpoint and use proper MCP SSE
# The FastMCP with transport="sse" should handle this automatically

# Debug FastMCP object to see available attributes
print(f"FastMCP attributes: {dir(mcp)}")

# Mount the FastMCP SSE app
try:
    if hasattr(mcp, 'sse_app'):
        print("Found mcp.sse_app - calling it to get the app")
        sse_app_instance = mcp.sse_app()  # Call the method to get the app
        app.mount("/mcp", sse_app_instance)
        print("Successfully mounted MCP SSE app at /mcp")
    else:
        print("No sse_app found")
        
except Exception as e:
    print(f"Error mounting MCP: {e}")
    # Create a simple SSE endpoint as fallback
    @app.get("/mcp")
    async def fallback_mcp_sse():
        async def event_generator():
            yield f"data: {json.dumps({'type': 'init', 'server': 'madhushala'})}\n\n"
            while True:
                await asyncio.sleep(30)
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"
        return EventSourceResponse(event_generator())

#mcp dev mcp_server.py
if __name__ == "__main__":
    import uvicorn
    # Run the combined FastAPI app
    uvicorn.run(app, host="0.0.0.0", port=8000)