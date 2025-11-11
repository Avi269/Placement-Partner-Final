#!/usr/bin/env python3
"""Quick test for TXT file upload fix"""

import requests
import tempfile
import os

BASE_URL = "http://127.0.0.1:8000"

# Create a temporary TXT file
offer_text = """Dear John Doe,

We are pleased to offer you the position of Senior Software Engineer at TechCorp Inc.

COMPENSATION:
- Annual CTC: ₹8,00,000
- Basic Salary: ₹4,00,000

TERMS:
- Probation Period: 6 months
- Notice Period: 60 days

Best regards,
HR Team"""

temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
temp_file.write(offer_text)
temp_file.close()

print("Testing TXT file upload to offer analysis...")
print(f"Temporary file: {temp_file.name}")

try:
    # Get CSRF token
    session = requests.Session()
    session.get(f"{BASE_URL}/offer-analysis/")
    
    csrf_token = session.cookies.get('csrftoken')
    
    # Upload the file
    with open(temp_file.name, 'rb') as f:
        files = {'file': ('offer.txt', f, 'text/plain')}
        data = {'context': 'Test upload'}
        
        if csrf_token:
            data['csrfmiddlewaretoken'] = csrf_token
        
        headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': f"{BASE_URL}/offer-analysis/"
        }
        if csrf_token:
            headers['X-CSRFToken'] = csrf_token
        
        response = session.post(
            f"{BASE_URL}/offer-analysis/",
            files=files,
            data=data,
            headers=headers,
            timeout=30
        )
    
    print(f"Response status: {response.status_code}")
    
    if response.status_code == 200:
        try:
            result = response.json()
            if result.get('success'):
                print("✅ SUCCESS: TXT file upload and analysis working!")
                print(f"   CTC: {result.get('ctc', 'N/A')}")
                print(f"   Probation: {result.get('probation_period', 'N/A')}")
                print(f"   Notice: {result.get('notice_period', 'N/A')}")
            else:
                print(f"❌ FAILED: {result.get('message', 'Unknown error')}")
        except:
            print("⚠️  Response is not JSON (might be HTML)")
    else:
        print(f"❌ FAILED: Status {response.status_code}")
        print(response.text[:200])

finally:
    # Cleanup
    os.remove(temp_file.name)
    print("Cleanup complete")
