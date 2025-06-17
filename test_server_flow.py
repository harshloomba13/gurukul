#!/usr/bin/env python3
"""
Test script to verify the server flow works locally
"""
import sys
import os
import asyncio

# Add server directory to path
sys.path.append('./server')

async def test_flow():
    print("=== Testing Server Flow Locally ===\n")
    
    # Test importing the graph module
    try:
        from local_graph.graph import invoke_graph
        print("✅ Successfully imported invoke_graph from server/local_graph/graph.py")
    except ImportError as e:
        print(f"❌ Failed to import invoke_graph: {e}")
        return
    
    # Test different types of messages
    test_messages = [
        ("advertise my Bengali event", "Should call handle_advertisement"),
        ("create a menu for birthday party", "Should call handle_writeup"), 
        ("send notification to guests", "Should call handle_notification"),
        ("generate todo list for event", "Should call handle_todo_list"),
        ("book a table for 4 people", "Should call handle_booking"),
        ("hello there", "Should call basic GPT")
    ]
    
    print("\n=== Testing Different Message Types ===")
    
    for message, expected in test_messages:
        print(f"\n📝 Testing: '{message}'")
        print(f"🎯 Expected: {expected}")
        
        try:
            result = await invoke_graph(message)
            print(f"✅ Response: {result[:100]}{'...' if len(result) > 100 else ''}")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_flow())