#!/usr/bin/env python3
"""
Test Cover Letter Generator and Offer Analysis Features
"""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def test_cover_letter_page():
    """Test if cover letter page loads"""
    print("\n" + "="*60)
    print("1️⃣  TESTING COVER LETTER PAGE LOAD")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/cover-letter/", timeout=10)
        if response.status_code == 200:
            print("✅ Cover letter page loaded successfully")
            print(f"   Status: {response.status_code}")
            print(f"   Content length: {len(response.text)} bytes")
            
            # Check if form elements exist
            if 'job_title' in response.text:
                print("   ✓ Job title field found")
            if 'company_name' in response.text:
                print("   ✓ Company name field found")
            if 'job_description' in response.text:
                print("   ✓ Job description field found")
            if 'resume_text' in response.text:
                print("   ✓ Resume text field found")
            
            return True
        else:
            print(f"❌ Failed to load cover letter page: Status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error loading cover letter page: {str(e)}")
        return False


def test_cover_letter_generation():
    """Test cover letter generation with POST request"""
    print("\n" + "="*60)
    print("2️⃣  TESTING COVER LETTER GENERATION")
    print("="*60)
    
    # Test data
    cover_letter_data = {
        'job_title': 'Senior Software Engineer',
        'company_name': 'TechCorp Inc.',
        'job_description': 'We are looking for a Senior Software Engineer with 5+ years of experience in Python, Django, and React. You will lead development teams and architect scalable solutions.',
        'applicant_name': 'John Doe',
        'applicant_email': 'john.doe@example.com',
        'resume_text': 'Experienced software engineer with 6+ years in full-stack development. Proficient in Python, Django, React, and AWS. Led multiple successful projects and mentored junior developers.',
        'custom_prompt': 'Focus on my technical leadership experience and Django expertise.'
    }
    
    try:
        print("\n📤 Sending cover letter generation request...")
        print(f"   Job: {cover_letter_data['job_title']} at {cover_letter_data['company_name']}")
        
        # Get CSRF token first
        session = requests.Session()
        session.get(f"{BASE_URL}/cover-letter/")
        
        # Try to get CSRF token from cookies
        csrf_token = None
        if 'csrftoken' in session.cookies:
            csrf_token = session.cookies['csrftoken']
        
        headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': f"{BASE_URL}/cover-letter/"
        }
        
        if csrf_token:
            headers['X-CSRFToken'] = csrf_token
            cover_letter_data['csrfmiddlewaretoken'] = csrf_token
        
        response = session.post(
            f"{BASE_URL}/cover-letter/",
            data=cover_letter_data,
            headers=headers,
            timeout=30
        )
        
        print(f"   Response status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('success'):
                    print("✅ Cover letter generated successfully!")
                    cover_letter = result.get('cover_letter', '')
                    print(f"\n📝 Generated Cover Letter ({len(cover_letter)} characters):")
                    print("-" * 60)
                    print(cover_letter[:500] + "..." if len(cover_letter) > 500 else cover_letter)
                    print("-" * 60)
                    return True
                else:
                    print(f"❌ Generation failed: {result.get('message', 'Unknown error')}")
                    return False
            except json.JSONDecodeError:
                # Non-JSON response, might be HTML
                print("⚠️  Received HTML response instead of JSON")
                if len(response.text) > 0:
                    print("   Page loaded but AJAX endpoint may not be working")
                return False
        else:
            print(f"❌ Failed with status code: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except requests.Timeout:
        print("❌ Request timed out (AI model may be slow or unavailable)")
        return False
    except Exception as e:
        print(f"❌ Error generating cover letter: {str(e)}")
        return False


def test_offer_analysis_page():
    """Test if offer analysis page loads"""
    print("\n" + "="*60)
    print("3️⃣  TESTING OFFER ANALYSIS PAGE LOAD")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/offer-analysis/", timeout=10)
        if response.status_code == 200:
            print("✅ Offer analysis page loaded successfully")
            print(f"   Status: {response.status_code}")
            print(f"   Content length: {len(response.text)} bytes")
            
            # Check if form elements exist
            if 'offer_text' in response.text or 'offer-file' in response.text:
                print("   ✓ Offer text/file input found")
            if 'analysis-results' in response.text:
                print("   ✓ Results container found")
            
            return True
        else:
            print(f"❌ Failed to load offer analysis page: Status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error loading offer analysis page: {str(e)}")
        return False


def test_offer_analysis():
    """Test offer letter analysis with POST request"""
    print("\n" + "="*60)
    print("4️⃣  TESTING OFFER LETTER ANALYSIS")
    print("="*60)
    
    # Sample offer letter
    offer_text = """Dear John Doe,

We are pleased to offer you the position of Senior Software Engineer at TechCorp Inc.

COMPENSATION:
- Annual CTC: ₹8,00,000
- Basic Salary: ₹4,00,000
- HRA: ₹1,60,000
- Special Allowance: ₹2,40,000

TERMS AND CONDITIONS:
- Probation Period: 6 months
- Notice Period: 60 days
- Working Hours: 9 AM - 6 PM (Monday to Friday)
- Location: Bangalore, India

BENEFITS:
- Health Insurance
- Provident Fund
- Annual Leave: 21 days
- Sick Leave: 12 days

Please sign and return this offer letter within 7 days.

Best regards,
HR Team
TechCorp Inc."""
    
    offer_data = {
        'text': offer_text,
        'context': 'Standard tech company offer for senior developer role.'
    }
    
    try:
        print("\n📤 Sending offer analysis request...")
        
        # Get CSRF token first
        session = requests.Session()
        session.get(f"{BASE_URL}/offer-analysis/")
        
        csrf_token = None
        if 'csrftoken' in session.cookies:
            csrf_token = session.cookies['csrftoken']
        
        headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': f"{BASE_URL}/offer-analysis/"
        }
        
        if csrf_token:
            headers['X-CSRFToken'] = csrf_token
            offer_data['csrfmiddlewaretoken'] = csrf_token
        
        response = session.post(
            f"{BASE_URL}/offer-analysis/",
            data=offer_data,
            headers=headers,
            timeout=30
        )
        
        print(f"   Response status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('success'):
                    print("✅ Offer letter analyzed successfully!")
                    
                    print(f"\n📊 Analysis Results:")
                    print("-" * 60)
                    print(f"   CTC: {result.get('ctc', 'Not detected')}")
                    print(f"   Probation Period: {result.get('probation_period', 'Not detected')}")
                    print(f"   Notice Period: {result.get('notice_period', 'Not detected')}")
                    
                    risk_flags = result.get('risk_flags', [])
                    print(f"\n   Risk Flags ({len(risk_flags)}):")
                    if risk_flags:
                        for flag in risk_flags:
                            print(f"      ⚠️  {flag}")
                    else:
                        print("      ✓ No risks identified")
                    
                    explanation = result.get('explanation', '')
                    if explanation:
                        print(f"\n   Summary:")
                        print(f"      {explanation[:200]}...")
                    
                    compensation = result.get('compensation_analysis', '')
                    if compensation:
                        print(f"\n   Compensation Analysis:")
                        print(f"      {compensation[:200]}...")
                    
                    print("-" * 60)
                    return True
                else:
                    print(f"❌ Analysis failed: {result.get('message', 'Unknown error')}")
                    return False
            except json.JSONDecodeError:
                print("⚠️  Received HTML response instead of JSON")
                return False
        else:
            print(f"❌ Failed with status code: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except requests.Timeout:
        print("❌ Request timed out (AI model may be slow or unavailable)")
        return False
    except Exception as e:
        print(f"❌ Error analyzing offer letter: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🚀 TESTING COVER LETTER & OFFER ANALYSIS FEATURES")
    print("="*60)
    print(f"   Base URL: {BASE_URL}")
    print(f"   Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        'cover_letter_page': False,
        'cover_letter_generation': False,
        'offer_analysis_page': False,
        'offer_analysis': False
    }
    
    # Test cover letter features
    results['cover_letter_page'] = test_cover_letter_page()
    time.sleep(1)
    results['cover_letter_generation'] = test_cover_letter_generation()
    
    time.sleep(2)
    
    # Test offer analysis features
    results['offer_analysis_page'] = test_offer_analysis_page()
    time.sleep(1)
    results['offer_analysis'] = test_offer_analysis()
    
    # Summary
    print("\n" + "="*60)
    print("📋 TEST SUMMARY")
    print("="*60)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"   {status} - {test_name.replace('_', ' ').title()}")
    
    print("-" * 60)
    print(f"   Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Features are working correctly.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check the issues above.")
        
        # Provide troubleshooting tips
        print("\n💡 Troubleshooting Tips:")
        if not results['cover_letter_generation']:
            print("   • Cover Letter Generation Issue:")
            print("     - Check if Gemini API key is configured")
            print("     - Verify AI model backend is working")
            print("     - Check Django logs for errors")
        if not results['offer_analysis']:
            print("   • Offer Analysis Issue:")
            print("     - Check if Gemini API key is configured")
            print("     - Verify text extraction is working")
            print("     - Check Django logs for errors")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()
