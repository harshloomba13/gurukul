import os
from anthropic import Anthropic
from twilio.rest import Client as TwilioClient
from instagrapi import Client as InstaClient

# --- Configuration ---
anu_whatsapp = os.environ.get("ANU_WHATSAPP")
twilio_sid = os.environ.get("TWILIO_SID") 
twilio_token = os.environ.get("TWILIO_TOKEN")
twilio_whatsapp_number = os.environ.get("TWILIO_WHATSAPP_NUMBER")
instagram_username = os.environ.get("INSTAGRAM_USERNAME")
instagram_password = os.environ.get("INSTAGRAM_PASSWORD")

def call_gpt(prompt):
    try:
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
    except Exception as e:
        print(f"=== Debug: GPT API error: {str(e)} ===")
        return f"Error generating content: {str(e)}"

def send_to_whatsapp(to_number, message):
    try:
        if not message or len(message.strip()) == 0:
            print("=== Debug: Empty message, skipping WhatsApp send ===")
            return
        
        if not all([twilio_sid, twilio_token, twilio_whatsapp_number, to_number]):
            print("=== Debug: Missing Twilio credentials, skipping WhatsApp send ===")
            return
        
        # Truncate message if it's too long for WhatsApp (1600 char limit)
        if len(message) > 1500:  # Leave some buffer
            message = message[:1500] + "..."
            print(f"=== Debug: Message truncated to {len(message)} characters ===")
        
        client = TwilioClient(twilio_sid, twilio_token)
        client.messages.create(body=message, from_=twilio_whatsapp_number, to=to_number)
        print("=== Debug: WhatsApp message sent successfully ===")
    except Exception as e:
        print(f"=== Debug: WhatsApp error: {str(e)} ===")

def post_to_instagram(caption):
    try:
        print("=== Debug: Attempting Instagram login ===")
        cl = InstaClient()
        cl.login(instagram_username, instagram_password)
        
        # Check if image file exists, if not skip image upload
        if not os.path.exists("image.jpeg"):
            print("=== Debug: No image file found, skipping Instagram post ===")
            return
            
        cl.photo_upload("image.jpeg", caption)
        print("=== Debug: Instagram post successful ===")
    except Exception as e:
        print(f"=== Debug: Instagram error: {str(e)} ===")

def postprocess_and_route(tool_name, content):
    if tool_name in ["handle_booking", "handle_notification", "handle_todo_list"]:
        send_to_whatsapp(anu_whatsapp, content)
    elif tool_name == "handle_advertisement":
        post_to_instagram(content)
        # send_to_whatsapp(anu_whatsapp, content)
    elif tool_name == "handle_writeup":
        send_to_whatsapp(anu_whatsapp, content)

def handle_advertisement(msg: str) -> str:
    result = call_gpt(f"Create a promotional Instagram + WhatsApp post for this event: {msg}")
    postprocess_and_route("handle_advertisement", result)
    return result

def handle_writeup(msg: str) -> str:
    print("=== Debug: Entering handle_writeup ===")
    print(f"Message received: {msg}")
    result = call_gpt(f"Suggest a menu and a poetic write-up for this event: {msg}")
    print("=== Debug: GPT response received ===")
    postprocess_and_route("handle_writeup", result)
    print("=== Debug: Exiting handle_writeup ===")
    return result

def handle_notification(msg: str) -> str:
    result = call_gpt(f"Write a WhatsApp reminder message to guests about: {msg}")
    postprocess_and_route("handle_notification", result)
    return result

def handle_todo_list(msg: str) -> str:
    result = call_gpt(f"Generate a checklist of things the event organizer needs to do before: {msg}")
    postprocess_and_route("handle_todo_list", result)
    return result

def handle_booking(msg: str) -> str:
    result = call_gpt(f"Create a booking confirmation or response for: {msg}")
    postprocess_and_route("handle_booking", result)
    return result