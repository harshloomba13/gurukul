import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Import tool functions directly from mcp_server
try:
    # Try importing from current directory first (for deployment)
    from mcp_server import handle_writeup, handle_advertisement, handle_notification, handle_todo_list, handle_booking, call_gpt as server_call_gpt
    print("✅ Successfully imported tool functions from mcp_server (current dir)")
except ImportError:
    try:
        # Try importing from parent directory (for local development)
        sys.path.append('..')
        from mcp_server import handle_writeup, handle_advertisement, handle_notification, handle_todo_list, handle_booking, call_gpt as server_call_gpt
        print("✅ Successfully imported tool functions from mcp_server (parent dir)")
    except ImportError as e:
        print(f"❌ Failed to import from mcp_server: {e}")
        # Fallback to basic GPT call
        from anthropic import Anthropic
    
        def server_call_gpt(prompt: str) -> str:
            try:
                api_key = os.environ.get("ANTHROPIC_API_KEY")
                if not api_key:
                    return "❌ Error: ANTHROPIC_API_KEY not set"
                anthropic = Anthropic(api_key=api_key)
                response = anthropic.messages.create(
                    max_tokens=2024,
                    model='claude-3-5-sonnet-20241022',
                    messages=[{'role': 'user', 'content': prompt}]
                )
                return response.content[0].text
            except Exception as e:
                return f"❌ Error: {str(e)}"

async def call_gpt(prompt: str) -> str:
    try:
        return server_call_gpt(prompt)
    except Exception as e:
        return f"❌ Error: {str(e)}"

async def invoke_graph(message: str) -> str:
    message_lower = message.lower()
    if "book" in message_lower:
        return await handle_booking_wrapper(message)
    elif "post" in message_lower or "advertise" in message_lower:
        return await handle_advertisement_wrapper(message)
    elif "menu" in message_lower or "writeup" in message_lower:
        return await handle_writeup_wrapper(message)
    elif "remind" in message_lower or "notify" in message_lower:
        return await handle_notification_wrapper(message)
    elif "todo" in message_lower or "checklist" in message_lower:
        return await handle_todo_list_wrapper(message)
    else:
        return await call_gpt("Reply helpfully to: " + message)

# Use the actual tool functions from mcp_server if available
async def handle_booking_wrapper(msg): 
    try:
        return handle_booking(msg)
    except:
        return await call_gpt(f"Take a booking request: '{msg}' and confirm it politely.")

async def handle_advertisement_wrapper(msg): 
    try:
        return handle_advertisement(msg)
    except:
        return await call_gpt(f"Create a promotional Instagram + WhatsApp post for this event: {msg}")

async def handle_writeup_wrapper(msg): 
    try:
        return handle_writeup(msg)
    except:
        return await call_gpt(f"Suggest a menu and a poetic write-up for this event: {msg}")

async def handle_notification_wrapper(msg): 
    try:
        return handle_notification(msg)
    except:
        return await call_gpt(f"Write a WhatsApp reminder message to guests about: {msg}")

async def handle_todo_list_wrapper(msg): 
    try:
        return handle_todo_list(msg)
    except:
        return await call_gpt(f"Generate a checklist of things the event organizer needs to do before: {msg}")