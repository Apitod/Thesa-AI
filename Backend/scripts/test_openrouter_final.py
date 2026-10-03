#!/usr/bin/env python
"""
Simple test untuk OpenRouter API dengan model sederhana
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_openrouter():
    """Test OpenRouter API connection dengan model sederhana"""

    api_key = os.getenv('OPENROUTER_API_KEY')
    api_url = os.getenv('OPENROUTER_API_URL')

    print("=" * 60)
    print("OPENROUTER API TEST (Simple Model)")
    print("=" * 60)

    print(f"API URL: {api_url}")
    print(f"API Key: {api_key[:10] if api_key else 'Not set'}")

    if not api_key:
        print("\n[FAIL] API key not configured")
        return False

    # Test payload dengan openai/gpt-3.5-turbo (model lebih sederhana)
    payload = {
        'model': 'openai/gpt-3.5-turbo',
        'messages': [
            {
                'role': 'system',
                'content': 'Anda adalah asisten akademik.'
            },
            {
                'role': 'user',
                'content': 'Hello! Say "working" in Indonesian.'
            }
        ],
        'max_tokens': 50
    }

    print(f"Model: {payload['model']}")

    try:
        print("\nSending request...")
        response = requests.post(api_url, headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
            'HTTP-Referer': 'https://openrouter.ai'
        }, json=payload, timeout=30)

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            if 'choices' in data:
                content = data['choices'][0]['message']['content']
                print(f"\n[SUCCESS] API Working!")
                print(f"AI Response: {content}")
                return True
            else:
                print(f"Response data: {data.keys()}")
                return True

        elif response.status_code == 401:
            print("\n[FAIL] Authentication Error")
            print("Try getting API key from OpenRouter dashboard")
            return False

        else:
            print(f"\n[FAIL] Status {response.status_code}")
            return False

    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        return False

if __name__ == "__main__":
    success = test_openrouter()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if success:
        print("[SUCCESS] OpenRouter API accessible!")
        print("\nRekomendasi:")
        print("1. Gunakan mode manual untuk mulai")
        print("2. Dapatkan API key yang working dari OpenRouter dashboard")
        print("3. Cek apakah API key Anda memiliki akses ke model openai/gpt-3.5-turbo")
        print("4. Hubungi support OpenRouter jika masalah berlanjut")
    else:
        print("[FAIL] OpenRouter API tidak dapat diakses")
        print("\nSistem Manual Mode tetap tersedia!")

    print("=" * 60)