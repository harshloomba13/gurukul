#!/usr/bin/env python3
"""Test script for the improved URL validation methods."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from client_ui import validate_figma_url

def test_validation_methods():
    """Test various validation scenarios."""
    
    test_url = "https://www.figma.com/design/MewdbgLi2pZnom6efzBGv3/Untitled?node-id=12-1793&t=oUpEloO1XGhzk3P2-1"
    
    print("🧪 Testing URL Validation Methods")
    print("=" * 50)
    print(f"Test URL: {test_url}")
    print()
    
    # Test 1: Normal validation (should fail with 403)
    print("1. Normal validation:")
    is_valid, message = validate_figma_url(test_url)
    print(f"   Valid: {is_valid}")
    print(f"   Message: {message}")
    print()
    
    # Test 2: Skip validation
    print("2. Skip validation:")
    is_valid, message = validate_figma_url(test_url, skip_validation=True)
    print(f"   Valid: {is_valid}")
    print(f"   Message: {message}")
    print()
    
    # Test 3: With mock Figma token
    print("3. With Figma token:")
    is_valid, message = validate_figma_url(test_url, figma_token="mock_token")
    print(f"   Valid: {is_valid}")
    print(f"   Message: {message}")
    print()
    
    # Test 4: Invalid URL format
    print("4. Invalid URL format:")
    is_valid, message = validate_figma_url("https://example.com/invalid")
    print(f"   Valid: {is_valid}")
    print(f"   Message: {message}")
    print()
    
    print("✅ All validation tests completed!")

if __name__ == "__main__":
    test_validation_methods()