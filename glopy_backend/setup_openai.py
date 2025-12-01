#!/usr/bin/env python3
"""
Setup script for OpenAI integration
"""

import os
import sys

def setup_openai_key():
    """Interactive setup for OpenAI API key"""
    print("🔧 OpenAI Setup for Glopy Assistant")
    print("=" * 50)
    
    # Check if key already exists
    existing_key = os.getenv('OPENAI_API_KEY')
    if existing_key:
        print(f"✅ OpenAI API key already set: {existing_key[:10]}...")
        return True
    
    print("\n📝 To get your OpenAI API key:")
    print("1. Go to https://platform.openai.com/")
    print("2. Sign up or log in")
    print("3. Navigate to API section")
    print("4. Create a new API key")
    print("5. Copy the key (starts with 'sk-')")
    
    print("\n🔑 Enter your OpenAI API key (or press Enter to skip):")
    api_key = input("API Key: ").strip()
    
    if not api_key:
        print("⚠️  No API key provided. Glopy Assistant will work with basic pattern matching.")
        return False
    
    if not api_key.startswith('sk-'):
        print("⚠️  Warning: API key doesn't start with 'sk-'. Please verify it's correct.")
        confirm = input("Continue anyway? (y/N): ").strip().lower()
        if confirm != 'y':
            return False
    
    # Set environment variable for current session
    os.environ['OPENAI_API_KEY'] = api_key
    print(f"✅ API key set for current session: {api_key[:10]}...")
    
    # Create .env file
    env_file = '.env'
    env_content = f"OPENAI_API_KEY={api_key}\n"
    
    try:
        with open(env_file, 'w') as f:
            f.write(env_content)
        print(f"✅ API key saved to {env_file}")
    except Exception as e:
        print(f"⚠️  Could not save to {env_file}: {e}")
        print("💡 You can manually set the environment variable:")
        print(f"   export OPENAI_API_KEY={api_key}")
    
    return True

def test_setup():
    """Test the setup"""
    print("\n🧪 Testing setup...")
    
    # Test import
    try:
        import openai
        print("✅ OpenAI library available")
    except ImportError:
        print("❌ OpenAI library not found. Run: pip install openai")
        return False
    
    # Test API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ No API key found")
        return False
    
    print(f"✅ API key found: {api_key[:10]}...")
    
    # Test client initialization
    try:
        client = openai.OpenAI(api_key=api_key)
        print("✅ OpenAI client initialized")
    except Exception as e:
        print(f"❌ Client initialization failed: {e}")
        return False
    
    # Test API call (optional)
    test_api = input("\n🧪 Test API call? (y/N): ").strip().lower()
    if test_api == 'y':
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello, this is a test."}],
                max_tokens=10
            )
            print("✅ API call successful!")
            print(f"📝 Response: {response.choices[0].message.content}")
        except Exception as e:
            print(f"❌ API call failed: {e}")
            return False
    
    return True

def main():
    """Main setup function"""
    print("🚀 Glopy Assistant OpenAI Setup")
    print("=" * 50)
    
    # Setup API key
    if setup_openai_key():
        # Test the setup
        if test_setup():
            print("\n🎉 Setup complete! Glopy Assistant is ready with OpenAI integration.")
            print("\n💡 Next steps:")
            print("1. Restart your Flask application")
            print("2. Go to /glopy-assistant")
            print("3. Try chatting with Glopy!")
        else:
            print("\n⚠️  Setup completed but testing failed. Check the errors above.")
    else:
        print("\n⚠️  Setup incomplete. Glopy Assistant will work with basic pattern matching.")
        print("💡 You can run this script again anytime to set up OpenAI.")

if __name__ == "__main__":
    main()
