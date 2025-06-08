import requests
import json

def test_api(message):
    """Simple HTTP client to test the deployed API"""
    api_url = "https://madhushala-api.onrender.com/agent"
    
    try:
        print(f"=== Sending request to {api_url} ===")
        print(f"Message: {message}")
        
        response = requests.post(api_url, 
                               json={"message": message},
                               timeout=60)  # Longer timeout for cloud
        
        print(f"=== Response Status: {response.status_code} ===")
        
        if response.status_code == 200:
            result = response.json()
            print(f"=== Response: ===")
            print(json.dumps(result, indent=2))
            return result
        else:
            print(f"Error: HTTP {response.status_code}")
            print(response.text)
            return None
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

if __name__ == "__main__":
    # Test different types of requests
    test_cases = [
        "Create a menu for a Bengali birthday party",
        "Advertise my upcoming Bengali event on May 31st in Vancouver",
        "Send notification to guests about the party",
        "Generate a todo list for organizing the event"
    ]
    
    for test_message in test_cases:
        print(f"\n{'='*50}")
        print(f"Testing: {test_message}")
        print(f"{'='*50}")
        test_api(test_message)
        print("\n")