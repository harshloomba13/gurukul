
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
openai = OpenAI(api_key='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')

def call_gpt(prompt: str) -> str:
    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
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
