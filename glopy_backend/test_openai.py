#!/usr/bin/env python3
"""
Test script to diagnose OpenAI integration issues
"""

import os
import sys

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If python-dotenv is not available, try to read .env manually
    try:
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    except FileNotFoundError:
        pass

def test_openai_import():
    """Test OpenAI import and version"""
    try:
        import openai
        print(f"✅ OpenAI imported successfully")
        print(f"📦 OpenAI version: {getattr(openai, '__version__', 'unknown')}")
        return True
    except ImportError as e:
        print(f"❌ OpenAI import failed: {e}")
        return False

def test_openai_client():
    """Test OpenAI client initialization"""
    try:
        import openai
        
        # Test API key
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("⚠️  No OPENAI_API_KEY environment variable found")
            return False
        
        print(f"🔑 API key found: {api_key[:10]}...")
        
        # Test client initialization
        try:
            client = openai.OpenAI(api_key=api_key)
            print("✅ OpenAI client initialized successfully (v1.0+ format)")
            return True
        except Exception as e1:
            print(f"❌ v1.0+ client initialization failed: {e1}")
            
            # Try older format
            try:
                openai.api_key = api_key
                print("✅ OpenAI client initialized successfully (v0.x format)")
                return True
            except Exception as e2:
                print(f"❌ v0.x client initialization failed: {e2}")
                return False
                
    except Exception as e:
        print(f"❌ OpenAI client test failed: {e}")
        return False

def test_openai_api_call():
    """Test actual API call"""
    try:
        import openai
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("⚠️  No API key available for testing")
            return False
        
        # Try v1.0+ format first
        try:
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello, this is a test."}],
                max_tokens=10
            )
            print("✅ OpenAI API call successful (v1.0+ format)")
            print(f"📝 Response: {response.choices[0].message.content}")
            return True
        except Exception as e1:
            print(f"❌ v1.0+ API call failed: {e1}")
            
            # Try v0.x format
            try:
                openai.api_key = api_key
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "Hello, this is a test."}],
                    max_tokens=10
                )
                print("✅ OpenAI API call successful (v0.x format)")
                print(f"📝 Response: {response.choices[0].message.content}")
                return True
            except Exception as e2:
                print(f"❌ v0.x API call failed: {e2}")
                return False
                
    except Exception as e:
        print(f"❌ OpenAI API test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing OpenAI Integration")
    print("=" * 50)
    
    # Test 1: Import
    print("\n1️⃣ Testing OpenAI import...")
    import_success = test_openai_import()
    
    # Test 2: Client initialization
    print("\n2️⃣ Testing OpenAI client initialization...")
    client_success = test_openai_client()
    
    # Test 3: API call (only if client works)
    if client_success:
        print("\n3️⃣ Testing OpenAI API call...")
        api_success = test_openai_api_call()
    else:
        print("\n3️⃣ Skipping API call test (client initialization failed)")
        api_success = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print(f"   Import: {'✅' if import_success else '❌'}")
    print(f"   Client: {'✅' if client_success else '❌'}")
    print(f"   API:    {'✅' if api_success else '❌'}")
    
    if all([import_success, client_success, api_success]):
        print("\n🎉 All tests passed! OpenAI integration should work.")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
        print("\n💡 Troubleshooting tips:")
        print("   - Make sure you have the correct OpenAI version installed")
        print("   - Check your API key is valid and has credits")
        print("   - Try: pip install --upgrade openai")
        print("   - Check your internet connection")

if __name__ == "__main__":
    main()
