
def invoke_graph(message: str) -> str:
    if "book" in message.lower():
        return handle_booking(message)
    elif "post" in message.lower() or "advertise" in message.lower():
        return handle_advertisement(message)
    elif "menu" in message.lower() or "writeup" in message.lower():
        return handle_writeup(message)
    elif "remind" in message.lower() or "notify" in message.lower():
        return handle_notification(message)
    elif "todo" in message.lower() or "checklist" in message.lower():
        return handle_todo_list(message)
    else:
        return "I'm here to help you with bookings, events, and reminders. How can I assist?"

def handle_booking(msg): return "✅ Booking created for your event. We'll follow up with confirmation."
def handle_advertisement(msg): return "📣 Draft Instagram/WhatsApp post created. Ready to publish!"
def handle_writeup(msg): return "🍽️ Here's a suggested menu and event writeup: Paneer Tikka, Kheer, and soulful poetry."
def handle_notification(msg): return "🔔 Guests have been notified via WhatsApp and Email."
def handle_todo_list(msg): return "📋 Organizer To-Do: Confirm caterer, test lights, print menus, cue sound check."
