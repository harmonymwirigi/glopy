#!/usr/bin/env python3
"""
Script to create OpenAI Assistant for Glopy
"""

import os
import sys
from dotenv import load_dotenv

def create_glopy_assistant():
    """Create OpenAI Assistant for Glopy"""
    load_dotenv()
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("No OPENAI_API_KEY found. Run setup_assistant.py first.")
        return
    
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        
        print("Creating Glopy Assistant...")
        asst_Mmla8NW3uSFvvF14S6o5uFRi
        # Create the assistant
        assistant = client.beta.assistants.create(
            name="Glopy Real Estate Assistant",
            instructions="""You are Glopy, a friendly and intelligent real estate assistant. You help users find properties by understanding their natural language queries and maintaining conversation context.

Your personality:
- Warm, friendly, and conversational like talking to a knowledgeable friend
- Intelligent and helpful with real estate expertise
- Use emojis naturally (🏠, 😊, 👍, etc.)
- Maintain conversation memory and context
- Ask follow-up questions to understand user needs better
- Provide detailed explanations about properties and recommendations

Your capabilities:
- Understand any natural language query about property search
- Remember conversation context and refine searches progressively
- Explain why properties match user criteria
- Suggest alternatives when exact matches aren't found
- Handle both English and Spanish conversations naturally

Always be helpful, honest, and conversational. Make users feel like they're talking to a real estate expert who truly cares about finding them the perfect property.""",
            model="gpt-3.5-turbo",
            tools=[]  # No tools needed - we handle function calls in our code
        )
        
        print(f"Assistant created successfully!")
        print(f"Assistant ID: {assistant.id}")
        print(f"Name: {assistant.name}")
        
        # Save to .env file
        with open('.env', 'a') as f:
            f.write(f"\nOPENAI_ASSISTANT_ID={assistant.id}\n")
        
        print("Assistant ID saved to .env file")
        print("\nGlopy Assistant is ready to use!")
        
    except ImportError:
        print("OpenAI library not installed. Run: pip install openai")
    except Exception as e:
        print(f"Error creating assistant: {e}")

if __name__ == "__main__":
    create_glopy_assistant()
