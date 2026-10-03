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

    # Try with different header formats
    headers_variations = [
        {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
            'HTTP-Referer': 'https://openrouter.ai'
        },
        {
            'Content-Type': 'application/json',
            'x-openrouter-key': api_key,
            'HTTP-Referer': 'https://openrouter.ai'
        }
    ]

    for i, headers in enumerate(headers_variations, 1):
        try:
            print(f"\nAttempt {i}: Using {list(headers.keys())}")

            response = requests.post(api_url, headers=headers, json=payload, timeout=10)

            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()

                if 'choices' in data:
                    content = data['choices'][0]['message']['content']
                elif 'message' in data:
                    content = data['message']['content'] if isinstance(data['message'], dict) else str(data['message'])

                print(f"\n[SUCCESS] Working with header combination: {list(headers.keys())}!")
                print(f"AI Response: {content}")

                return True

            elif response.status_code != 200:
                print(f"Response: {response.text[:200]}")

        except Exception as e:
            print(f"Error with {list(headers.keys())}: {str(e)}")

    # If all fail, try original header
    print("\nAttempt 3: Using original Authorization header")

    try:
        response = requests.post(api_url, headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
            'HTTP-Referer': 'https://openrouter.ai'
        }, json=payload, timeout=10)

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            if 'choices' in data:
                content = data['choices'][0]['message']['content']
            elif 'message' in data:
                    content = data['message']['content'] if isinstance(data['message'], dict) else str(data['message'])

            print(f"\n[SUCCESS] Working with Authorization header!")
            print(f"AI Response: {content}")

            return True

        else:
            print(f"Response: {response.text[:200]}")

    except Exception as e:
        print(f"Error with Authorization header: {str(e)}")

    return False

        elif response.status_code == 401:
            print("\n[FAIL] Authentication Error")
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', str(error_data))
                print(f"Error: {error_msg}")
            except:
                print(f"Response: {response.text[:200]}")

            return False

        elif response.status_code == 402:
            print("\n[FAIL] Payment Required")
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', str(error_data))
                print(f"Error: {error_msg}")
            except:
                print(f"Response: {response.text[:200]}")

            return False

        elif response.status_code == 429:
            print("\n[FAIL] Rate Limit")
            return False

        else:
            print(f"\n[FAIL] Unexpected Status: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return False

    except requests.exceptions.Timeout:
        print("\n[FAIL] Connection Timeout")
        return False

    except requests.exceptions.ConnectionError as e:
        print(f"\n[FAIL] Connection Error: {str(e)}")
        return False

    except Exception as e:
        print(f"\n[FAIL] Error: {str(e)}")
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