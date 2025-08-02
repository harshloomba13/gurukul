#!/usr/bin/env python3
"""
Test script to verify Gemini API is working correctly
"""

import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_gemini_api():
    """Test if Gemini API is working"""
    
    # Load environment variables
    load_dotenv()
    
    # Get API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("❌ GEMINI_API_KEY not found in environment variables")
        print("Please set GEMINI_API_KEY in your .env file")
        return False
    
    logger.info("✅ GEMINI_API_KEY found")
    
    try:
        # Initialize LLM
        llm = ChatGoogleGenerativeAI(
            model="gemini/gemini-1.5-flash",
            temperature=0.2,
            google_api_key=api_key
        )
        logger.info("✅ LLM initialized successfully")
        
        # Test a simple call
        response = llm.invoke("Hello! Please respond with 'API is working' if you can see this message.")
        logger.info(f"✅ API test successful: {response.content}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ API test failed: {str(e)}")
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing Gemini API...")
    success = test_gemini_api()
    if success:
        print("✅ Gemini API is working correctly!")
    else:
        print("❌ Gemini API test failed. Check your API key and internet connection.") 