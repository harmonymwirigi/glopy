#!/usr/bin/env python3
"""
Setup script for OpenAI Assistant configuration
"""

import os
import sys
from dotenv import load_dotenv

def setup_openai_assistant():
    """Interactive setup for OpenAI Assistant"""
    print("Glopy Assistant Setup")
    print("=" * 50)
    
    # Load existing .env file
    load_dotenv()
    
    # Check for API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("No OPENAI_API_KEY found in .env file")
        api_key = input("Enter your OpenAI API key: ").strip()
        if api_key:
            with open('.env', 'a') as f:
                f.write(f"\nOPENAI_API_KEY={api_key}\n")
            print("API key saved to .env file")
        else:
            print("No API key provided. Exiting.")
            return
    else:
        print(f"API key found: {api_key[:10]}...")
    
    # Check for Assistant ID
    assistant_id = os.getenv('OPENAI_ASSISTANT_ID')
    if not assistant_id:
        print("\nAssistant ID not found in .env file")
        print("\nTo create an OpenAI Assistant:")
        print("1. Go to https://platform.openai.com/assistants")
        print("2. Click 'Create' to create a new assistant")
        print("3. Configure:")
        print("   - Name: Glopy Real Estate Assistant")
        print("   - Instructions: You are Glopy, a friendly and intelligent real estate assistant.")
        print("   - Model: gpt-3.5-turbo or gpt-4")
        print("   - Tools: None")
        print("4. Save and copy the Assistant ID")
        
        assistant_id = input("\nEnter your Assistant ID (or press Enter to skip): ").strip()
        if assistant_id:
            with open('.env', 'a') as f:
                f.write(f"OPENAI_ASSISTANT_ID={assistant_id}\n")
            print("Assistant ID saved to .env file")
        else:
            print("No Assistant ID provided. Will use chat completions instead.")
    else:
        print(f"Assistant ID found: {assistant_id}")
    
    # Test the setup
    print("\nTesting setup...")
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        
        # Test API key
        print("Testing API key...")
        # Simple test - list models
        models = client.models.list()
        print("API key is valid")
        
        # Test Assistant if ID provided
        if assistant_id:
            print("Testing Assistant...")
            try:
                assistant = client.beta.assistants.retrieve(assistant_id)
                print(f"Assistant found: {assistant.name}")
            except Exception as e:
                print(f"Assistant test failed: {e}")
                print("Please check your Assistant ID")
        
        print("\nSetup completed successfully!")
        print("The Glopy Assistant is ready to use.")
        
    except ImportError:
        print("OpenAI library not installed. Run: pip install openai")
    except Exception as e:
        print(f"Setup test failed: {e}")
        print("Please check your API key and try again.")

if __name__ == "__main__":
    setup_openai_assistant()
