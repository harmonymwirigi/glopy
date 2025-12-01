#!/usr/bin/env python3
"""
Test the improved smart assistant behavior
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from services.glopy_assistant import GlopyAssistant

def test_smart_assistant():
    """Test the smart assistant behavior"""
    with app.app_context():
        print("Testing Smart Assistant Behavior...")
        
        # Initialize the assistant
        assistant = GlopyAssistant()
        user_id = 1
        
        # Test 1: Initial greeting - should not search
        print("\n=== Test 1: Initial Greeting ===")
        response1 = assistant.process_message("hey", user_id=user_id)
        print(f"User: hey")
        print(f"Glopy: {response1['response']}")
        print(f"Properties found: {response1['property_count']}")
        print(f"Search criteria: {response1.get('search_criteria', {})}")
        
        # Test 2: Property request without enough info - should ask for more info
        print("\n=== Test 2: Incomplete Request ===")
        response2 = assistant.process_message("I am looking for a 5 bedroom house with a swimming pool", user_id=user_id)
        print(f"User: I am looking for a 5 bedroom house with a swimming pool")
        print(f"Glopy: {response2['response']}")
        print(f"Properties found: {response2['property_count']}")
        print(f"Search criteria: {response2.get('search_criteria', {})}")
        
        # Test 3: Adding price range - should now search
        print("\n=== Test 3: Adding Price Range ===")
        response3 = assistant.process_message("it should range from 1500 to 2000", user_id=user_id)
        print(f"User: it should range from 1500 to 2000")
        print(f"Glopy: {response3['response']}")
        print(f"Properties found: {response3['property_count']}")
        print(f"Search criteria: {response3.get('search_criteria', {})}")
        
        # Test 4: Confirming any type - should search with full criteria
        print("\n=== Test 4: Confirming Any Type ===")
        response4 = assistant.process_message("any of them is okay", user_id=user_id)
        print(f"User: any of them is okay")
        print(f"Glopy: {response4['response']}")
        print(f"Properties found: {response4['property_count']}")
        print(f"Search criteria: {response4.get('search_criteria', {})}")

if __name__ == "__main__":
    test_smart_assistant()
