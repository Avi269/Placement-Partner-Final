"""
Test Gemini API connection directly
"""
import google.generativeai as genai
from decouple import config

# Load API key
API_KEY = config('GEMINI_API_KEY')
print(f"✅ API Key loaded: {API_KEY[:20]}...{API_KEY[-4:]}")

# Configure Gemini
genai.configure(api_key=API_KEY)

# Test with multiple models
models_to_test = [
    'gemini-2.5-flash',
    'gemini-2.5-pro',
    'gemini-pro-latest',
    'gemini-2.0-flash',
]

print("\n🧪 Testing models:")
for model_name in models_to_test:
    try:
        print(f"\n  Testing {model_name}...")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Say 'Hello' in 5 words")
        print(f"  ✅ {model_name}: {response.text[:50]}")
        print(f"  🎯 Use this model!")
        break  # Stop at first working model
    except Exception as e:
        if '429' in str(e) or 'quota' in str(e).lower():
            print(f"  ❌ {model_name}: Quota exceeded")
        elif '404' in str(e):
            print(f"  ❌ {model_name}: Not available")
        else:
            print(f"  ❌ {model_name}: {str(e)[:50]}")