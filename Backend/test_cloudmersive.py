import os
from dotenv import load_dotenv
import requests

load_dotenv()

key = os.environ.get("CLOUDMERSIVE_API_KEY")
print(f"Key: {key}")

url = 'https://api.cloudmersive.com/convert/docx/to/pdf'
headers = {'Apikey': key}

docx_path = r'D:\neomakalah\output\test_toc.docx' # Pick an existing file

try:
    with open(docx_path, 'rb') as f:
        files = {'inputFile': (os.path.basename(docx_path), f)}
        print("Sending request...")
        response = requests.post(url, headers=headers, files=files, timeout=60)
        
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Text: {response.text}")
    else:
        print("Success")
except Exception as e:
    print(e)
