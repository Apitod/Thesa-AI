#!/usr/bin/env python
"""
Simple test untuk OpenRouter API connection
"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def test_openrouter():
    """Test OpenRouter API connection"""

    api_key = os.getenv('OPENROUTER_API_KEY')
    api_url = os.getenv('OPENROUTER_API_URL')

    print("=" * 60)
    print("OPENROUTER API CONNECTION TEST")
    print("=" * 60)

    print(f"\nAPI URL: {api_url}")
    print(f"API Key: {api_key[:10]}...{api_key[-4:] if api_key else 'Not set'}")

    if not api_key or api_key == 'your_openrouter_api_key_here':
        print("\n[FAIL] API key not configured")
        return False

    # Test payload
    payload = {
        'model': 'qwen/qwen2.5-7b-instruct-free',
        'messages': [
            {
                'role': 'system',
                'content': 'Anda adalah asisten akademik.'
            },
            {
                'role': 'user',
                'content': 'Hello! Say "API connection successful" in Indonesian in exactly 3 words.'
            }
        ],
        'max_tokens': 50
    }

    print(f"\nRequest Model: {payload['model']}")
    print(f"Messages: {len(payload['messages'])}")

    # Try standard Authorization header
    print("\nTest 1: Standard Authorization header")

    try:
        response = requests.post(api_url, headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
            'HTTP-Referer': 'https://openrouter.ai'
        }, json=payload, timeout=30)

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            # Extract content from different response formats
            if 'choices' in data:
                content = data['choices'][0]['message']['content']
            elif 'message' in data:
                content = data['message']['content'] if isinstance(data['message'], dict) else str(data['message'])

            print(f"\n[SUCCESS] API Working!")
            print(f"AI Response: {content}")
            return True

        else:
            print(f"Response: {response.text[:200]}")

    except Exception as e:
        print(f"Error: {str(e)}")

    # If standard fails, try alternate header
    print("\nTest 2: x-openrouter-key header")

    try:
        response = requests.post(api_url, headers={
            'Content-Type': 'application/json',
            'x-openrouter-key': api_key,
            'HTTP-Referer': 'https://openrouter.ai'
        }, json=payload, timeout=30)

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            if 'choices' in data:
                content = data['choices'][0]['message']['content']
            elif 'message' in data:
                content = data['message']['content'] if isinstance(data['message'], dict) else str(data['message'])

            print(f"\n[SUCCESS] Working with x-openrouter-key!")
            print(f"AI Response: {content}")
            return True

        else:
            print(f"Response: {response.text[:200]}")

    except Exception as e:
        print(f"Error: {str(e)}")

    return False

if __name__ == "__main__":
    success = test_openrouter()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if success:
        print("[SUCCESS] OpenRouter API is working!")
        print("\nSistem siap digunakan dengan model:")
        print("  Primary: qwen/qwen2.5-7b-instruct-free")
        print("  Backup: openai/gpt-oss-120b:free (jika dikonfigurasi)")
    else:
        print("[FAIL] OpenRouter API not working")
        print("\nSuggestions:")
        print("1. Check API key in .env file")
        print("2. Check balance at OpenRouter dashboard")
        print("3. Use manual mode as fallback")

    print("=" * 60)