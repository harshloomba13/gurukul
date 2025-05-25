import os
#del os.environ["OPENAI_API_KEY"]  # Clears cached var
from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI
from mcp_client import MCP_ChatBot

print("Environment variables loaded:", os.environ.get("OPENAI_API_KEY", "Not found"))
openai = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "Not found"))

async def call_gpt(prompt: str) -> str:
    try:
        #response = openai.chat.completions.create(
        #    model="gpt-4",
        #    messages=[{"role": "user", "content": prompt}]
        #)
        #return response.choices[0].message.content.strip()
        chatbot = MCP_ChatBot()
        response = await chatbot.connect_to_server_and_run(messages=prompt)  # Just connect without running chat loop
        print(f"response :{response}")
        return response
    except Exception as e:
        return f"❌ Error: {str(e)}"

def invoke_graph(message: str) -> str:
    message_lower = message.lower()
    if "book" in message_lower:
        return handle_booking(message)
    elif "post" in message_lower or "advertise" in message_lower:
        return handle_advertisement(message)
    elif "menu" in message_lower or "writeup" in message_lower:
        return handle_writeup(message)
    elif "remind" in message_lower or "notify" in message_lower:
        return handle_notification(message)
    elif "todo" in message_lower or "checklist" in message_lower:
        return handle_todo_list(message)
    else:
        return call_gpt("Reply helpfully to: " + message)

def handle_booking(msg): return call_gpt(f"Take a booking request: '{msg}' and confirm it politely.")
def handle_advertisement(msg): return call_gpt(f"Create a promotional Instagram + WhatsApp post for this event: {msg}")
def handle_writeup(msg): return call_gpt(f"Suggest a menu and a poetic write-up for this event: {msg}")
def handle_notification(msg): return call_gpt(f"Write a WhatsApp reminder message to guests about: {msg}")
def handle_todo_list(msg): return call_gpt(f"Generate a checklist of things the event organizer needs to do before: {msg}")
