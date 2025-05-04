import requests
import re

def create_event_tool(event_description: str) -> str:
    """
    Schedule and advertise a Madhushala event.
    The input should be a string describing the event in natural language.
    Example: "Create a Ghazal Night event on June 20 with biryani, jalebi, and shayari for ₹1800"
    """
    try:
        # Extract date using regex
        date_match = re.search(r'on\s+(\w+\s+\d+)', event_description)
        date = date_match.group(1) if date_match else "2024-12-31"  # Default date if not found
        
        # Extract price using regex
        price_match = re.search(r'₹(\d+)', event_description)
        price = int(price_match.group(1)) if price_match else 0
        
        # Extract menu items
        menu_match = re.search(r'with\s+([^.]+)', event_description)
        menu = [item.strip() for item in menu_match.group(1).split(',')] if menu_match else []
        
        # Extract features (everything after menu items)
        features_match = re.search(r'and\s+([^.]+)', event_description)
        features = [feature.strip() for feature in features_match.group(1).split(',')] if features_match else []
        
        # Extract title (everything before "on")
        title_match = re.search(r'Create\s+a\s+(.*?)\s+on', event_description)
        title = title_match.group(1) if title_match else "Unknown Event"
        
        event = {
            "title": title,
            "date": date,
            "menu": menu,
            "price": price,
            "features": features
        }
        
        res = requests.post("http://localhost:8000/create-event", json=event)
        if res.status_code == 200:
            data = res.json()
            return f"✅ Event '{title}' created successfully with ID: {data['event_id']}"
        else:
            return f"❌ Failed to create event: {res.text}"
    except Exception as e:
        return f"🚨 Error calling MCP server: {str(e)}"
