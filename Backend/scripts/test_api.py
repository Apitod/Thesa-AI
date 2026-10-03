#!/usr/bin/env python
"""
Script untuk mengetes koneksi API
"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def test_api_connection():
    """Test koneksi API dengan detail error"""

    print("=" * 60)
    print("API CONNECTION TEST")
    print("=" * 60)

    api_key = os.getenv('ZAI_API_KEY')
    api_url = os.getenv('ZAI_API_URL')

    print(f"\n[1] Configuration Check:")
    print(f"    API URL: {api_url}")
    print(f"    API Key: {api_key[:10]}...{api_key[-4:] if api_key else 'Not set'}")

    if not api_key or api_key == 'your_api_key_here':
        print("\n[FAIL] API key tidak diatur atau masih default.")
        print("Action: Set API key di file .env")
        return False

    if not api_url:
        print("\n[FAIL] API URL tidak diatur.")
        print("Action: Set API URL di file .env")
        return False

    print(f"\n[2] Testing connection...")

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }

    test_payload = {
        'model': 'glm-4-plus',
        'messages': [
            {
                'role': 'user',
                'content': 'Hello! Please respond with "API connection successful" in Indonesian.'
            }
        ],
        'max_tokens': 50
    }

    try:
        print(f"    Sending request to: {api_url}")
        response = requests.post(api_url, headers=headers, json=test_payload, timeout=30)

        print(f"    Response Status: {response.status_code}")
        print(f"    Response Time: {response.elapsed.total_seconds():.2f}s")

        if response.status_code == 200:
            print("\n[OK] API Connection Successful!")
            try:
                response_data = response.json()

                if 'choices' in response_data:
                    content = response_data['choices'][0]['message']['content']
                    print(f"    AI Response: {content[:100]}")
                else:
                    print("    Response format: Non-standard")
                    print(f"    Response keys: {list(response_data.keys())}")

                print("\n[OK] API is ready to use!")
                return True

            except json.JSONDecodeError:
                print("\n[FAIL] Response is not valid JSON")
                print(f"    Response: {response.text[:200]}")
                return False

        elif response.status_code == 401:
            print("\n[FAIL] Authentication Error")
            print("    Issue: API key tidak valid atau expired")
            print("    Action: Cek API key di file .env")
            print(f"    Current key: {api_key[:10]}...{api_key[-4:]}")
            return False

        elif response.status_code == 403:
            print("\n[FAIL] Access Denied")
            print("    Issue: Tidak memiliki akses ke API ini")
            print("    Action: Cek izin dan plan API key")
            return False

        elif response.status_code == 429:
            print("\n[FAIL] Rate Limit")
            print("    Issue: Terlalu banyak requests")
            print("    Action: Tunggu beberapa saat")
            return False

        elif response.status_code == 500:
            print("\n[FAIL] Server Error")
            print("    Issue: API server mengalami error")
            print("    Action: Coba lagi nanti")
            print(f"    Response: {response.text[:200]}")
            return False

        else:
            print(f"\n[FAIL] Unexpected Status Code: {response.status_code}")
            print(f"    Response: {response.text[:500]}")
            return False

    except requests.exceptions.Timeout:
        print("\n[FAIL] Connection Timeout")
        print("    Issue: Server tidak merespons dalam 30 detik")
        print("    Action: Cek koneksi internet dan API status")
        return False

    except requests.exceptions.ConnectionError as e:
        print(f"\n[FAIL] Connection Error")
        print(f"    Issue: {str(e)}")
        print("    Action: Cek koneksi internet dan API URL")
        print(f"    API URL yang dicoba: {api_url}")
        return False

    except Exception as e:
        print(f"\n[FAIL] Unexpected Error")
        print(f"    Error: {str(e)}")
        import traceback
        print(f"    Traceback: {traceback.format_exc()}")
        return False

def suggest_fixes():
    """Menampilkan saran perbaikan"""
    print("\n" + "=" * 60)
    print("SUGGESTED FIXES")
    print("=" * 60)

    print("""
[1] Cek API Key:
   - Pastikan API key benar
   - API key tidak expired
   - API key memiliki izin untuk chat/completion

[2] Cek API URL:
   - Pastikan URL API benar
   - Coba URL alternatif jika tersedia

[3] Cek Koneksi Internet:
   - Pastikan koneksi internet aktif
   - Coba akses API via browser/Postman

[4] Cek Status API:
   - Cek status server API provider
   - Cek jika ada maintenance scheduled

[5] Ganti API Provider:
   - Jika Z.ai tidak berfungsi, coba provider lain
   - Bisa menggunakan OpenAI, Anthropic, dll

[6] Gunakan Mode Manual:
   - Jika API tidak berfungsi, gunakan mode manual
   - Tidak membutuhkan koneksi internet
""")

if __name__ == "__main__":
    success = test_api_connection()

    if not success:
        suggest_fixes()

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)