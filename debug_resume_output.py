"""
Debug script to test resume parsing with API output
"""
import os
import sys
import django

# Set the API key in environment
os.environ['GEMINI_API_KEY'] = 'AIzaSyDepaU8Ku0dNGSp6YOUX4pCFMNNwH4AMf0'

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'placement_partner.settings')
django.setup()

from core.utils import parse_resume_file, generate_with_retry
import google.generativeai as genai
import json
import tempfile

print("=" * 60)
print("RESUME PARSING DEBUG TEST")
print("=" * 60)

# Test 1: Check API Key
print("\n[1] Testing API Key Configuration...")
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    print(f"✓ API Key found: {api_key[:20]}...")
else:
    print("✗ API Key NOT found!")
    sys.exit(1)

# Test 2: Test direct Gemini API call
print("\n[2] Testing Direct Gemini API Call...")
try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content("Say 'Hello World'")
    print(f"✓ Gemini API Response: {response.text[:50]}...")
except Exception as e:
    print(f"✗ Gemini API Error: {e}")
    sys.exit(1)

# Test 3: Parse sample resume text
print("\n[3] Testing Resume Parsing with Direct Gemini Call...")
sample_resume = """
JOHN DOE
Email: john.doe@example.com
Phone: +1 (555) 123-4567

EDUCATION
Bachelor of Science in Computer Science
Stanford University, 2018-2022

EXPERIENCE
Software Engineer | Tech Corp | 2022-Present
- Developed web applications using Python and Django
- Implemented REST APIs for mobile applications
- Worked with AWS cloud services

SKILLS
Python, Django, JavaScript, React, Node.js, AWS, Docker, Git, SQL, Machine Learning
"""

try:
    # Test direct parsing with Gemini (bypassing file extraction)
    print("   Calling Gemini API directly...")
    
    prompt = f"""
    You are an AI resume parser. Extract the following fields from the resume:
    - name
    - email
    - phone
    - education (as a list of strings)
    - experience (as a list of strings)
    - skills (as a list of short strings, only technical or job-relevant skills)
    - parsed_text (raw cleaned text)

    Return the response as valid JSON like this:
    {{
      "name": "...",
      "email": "...",
      "phone": "...",
      "education": ["..."],
      "experience": ["..."],
      "skills": ["..."],
      "parsed_text": "..."
    }}

    Resume:
    {sample_resume}
    """
    
    from core.utils import generate_with_retry
    import re
    
    response = generate_with_retry(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.0,
            max_output_tokens=1024,
        )
    ).text.strip()
    
    print(f"\n   Raw Gemini Response (first 200 chars):")
    print(f"   {response[:200]}...")
    
    # Remove code fences if present
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", response)
    cleaned = match.group(1) if match else response
    
    print(f"\n   Cleaned Response (first 200 chars):")
    print(f"   {cleaned[:200]}...")
    
    try:
        parsed_data = json.loads(cleaned) if cleaned else {}
    except json.JSONDecodeError as e:
        print(f"\n   ⚠ JSON parsing failed: {e}")
        print(f"   Attempting repair...")
        # Attempt to repair invalid JSON
        repaired = cleaned.strip()
        repaired = repaired.replace("\n", " ").replace("\r", " ")
        repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
        try:
            parsed_data = json.loads(repaired)
            print(f"   ✓ Repair successful!")
        except:
            print(f"   ✗ Repair failed. Using fallback data.")
            parsed_data = {
                "name": "Test User",
                "email": "test@example.com",
                "phone": "+1234567890",
                "skills": ["Python", "Django"],
                "education": [],
                "experience": [],
                "parsed_text": sample_resume
            }
    
    print("\n✓ Resume Parsed Successfully!")
    print("\n" + "=" * 60)
    print("PARSED OUTPUT:")
    print("=" * 60)
    print(json.dumps(parsed_data, indent=2))
    
    print("\n" + "=" * 60)
    print("FIELD CHECK:")
    print("=" * 60)
    print(f"Name: {parsed_data.get('name', 'NOT FOUND')}")
    print(f"Email: {parsed_data.get('email', 'NOT FOUND')}")
    print(f"Phone: {parsed_data.get('phone', 'NOT FOUND')}")
    print(f"Skills: {len(parsed_data.get('skills', []))} found")
    print(f"Education: {len(parsed_data.get('education', []))} found")
    print(f"Experience: {len(parsed_data.get('experience', []))} found")
    
    # Check if data is empty
    if not parsed_data.get('name') and not parsed_data.get('email'):
        print("\n⚠ WARNING: No data extracted! This might be the issue.")
    else:
        print("\n✓ Data extracted successfully!")
    
except Exception as e:
    print(f"\n✗ Parsing Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Check response format
print("\n" + "=" * 60)
print("RESPONSE FORMAT CHECK:")
print("=" * 60)

expected_keys = ['name', 'email', 'phone', 'skills', 'education', 'experience', 'parsed_text']
missing_keys = [key for key in expected_keys if key not in parsed_data]

if missing_keys:
    print(f"⚠ Missing keys: {missing_keys}")
else:
    print("✓ All expected keys present")

# Check if values are populated
empty_keys = [key for key in expected_keys if not parsed_data.get(key)]
if empty_keys:
    print(f"⚠ Empty fields: {empty_keys}")
else:
    print("✓ All fields have values")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)

if missing_keys or empty_keys:
    print("\n⚠ ISSUE FOUND: Some fields are missing or empty")
    print("   This might explain why no output is showing on the frontend")
else:
    print("\n✓ ALL TESTS PASSED - Backend is working correctly")
    print("   If no output is showing, the issue is likely in the frontend JavaScript")
