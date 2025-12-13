"""
Test script to verify text extraction and job search fixes
Run this to check if the improvements are working correctly
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'placement_partner.settings')
django.setup()

from core.utils import parse_resume_file, extract_text_from_file, extract_skills_from_text
from core.job_search import fetch_jobs_for_skills

def test_pdf_extraction():
    """Test PDF extraction with multiple strategies"""
    print("\n" + "="*70)
    print("TEST 1: PDF TEXT EXTRACTION")
    print("="*70)
    
    # Check if there are any resumes in media/resumes/
    resume_dir = "media/resumes/"
    if os.path.exists(resume_dir):
        resumes = [f for f in os.listdir(resume_dir) if f.endswith('.pdf')]
        if resumes:
            test_file = os.path.join(resume_dir, resumes[0])
            print(f"\n✓ Testing with: {test_file}")
            
            try:
                text = extract_text_from_file(test_file)
                if text and len(text) > 50:
                    print(f"✓ SUCCESS: Extracted {len(text)} characters")
                    print(f"✓ Preview: {text[:200]}...")
                    return True
                else:
                    print("✗ FAILED: No text extracted or text too short")
                    return False
            except Exception as e:
                print(f"✗ FAILED: {str(e)}")
                return False
        else:
            print("⚠ No PDF files found in media/resumes/")
    else:
        print("⚠ Resume directory not found")
    
    return None


def test_resume_parsing():
    """Test complete resume parsing with AI fallback"""
    print("\n" + "="*70)
    print("TEST 2: RESUME PARSING (Name, Email, Phone, Skills)")
    print("="*70)
    
    # Sample resume text for testing
    sample_resume_text = """
    JOHN DOE
    Email: john.doe@example.com
    Phone: +91 98765-43210
    
    EDUCATION
    B.Tech in Computer Science Engineering
    Indian Institute of Technology, Delhi
    2019-2023
    Roll No: 12345678
    
    SKILLS
    • Python, Django, Flask
    • JavaScript, React, Node.js
    • SQL, MongoDB
    • Docker, Kubernetes
    • Machine Learning, TensorFlow
    
    EXPERIENCE
    Software Engineer at Google
    June 2023 - Present
    • Developed web applications using Django
    • Implemented REST APIs
    
    PROJECTS
    E-commerce Website
    • Built using React and Django
    """
    
    print("\n✓ Testing with sample resume text...")
    
    try:
        from core.utils import enrich_parsed_resume
        
        # Simulate parsed data that needs enrichment
        parsed = {
            "parsed_text": sample_resume_text,
            "name": "",
            "email": "",
            "phone": "",
            "skills": [],
            "education": [],
            "experience": []
        }
        
        # Enrich with force extraction
        result = enrich_parsed_resume(parsed, fallback_text=sample_resume_text, force_extraction=True)
        
        print("\n" + "-"*70)
        print("EXTRACTION RESULTS:")
        print("-"*70)
        
        success_count = 0
        total_tests = 5
        
        # Test Name (should be "JOHN DOE" or "John Doe", NOT "Computer Science Engineering")
        if result.get("name"):
            name = result["name"]
            if "computer" not in name.lower() and "engineering" not in name.lower():
                print(f"✓ Name: {name}")
                success_count += 1
            else:
                print(f"✗ Name: {name} (incorrect - picked up degree instead of name)")
        else:
            print("✗ Name: Not found")
        
        # Test Email
        if result.get("email") and "@" in result["email"]:
            print(f"✓ Email: {result['email']}")
            success_count += 1
        else:
            print(f"✗ Email: {result.get('email', 'Not found')}")
        
        # Test Phone (should NOT pick up roll number)
        if result.get("phone"):
            phone = result["phone"]
            # Check if it's the phone number and not the roll number
            if "98765" in phone or "9876543210" in phone:
                print(f"✓ Phone: {phone} (correct)")
                success_count += 1
            elif "12345678" in phone:
                print(f"✗ Phone: {phone} (WRONG - picked up roll number)")
            else:
                print(f"⚠ Phone: {phone} (verify manually)")
                success_count += 0.5
        else:
            print("✗ Phone: Not found")
        
        # Test Skills
        if result.get("skills") and len(result["skills"]) > 0:
            print(f"✓ Skills: Found {len(result['skills'])} skills")
            print(f"  {', '.join(result['skills'][:10])}")
            success_count += 1
        else:
            print("✗ Skills: Not found")
        
        # Test Education
        if result.get("education") and len(result["education"]) > 0:
            print(f"✓ Education: Found {len(result['education'])} entries")
            success_count += 1
        else:
            print("⚠ Education: Not found (may be normal)")
        
        print("\n" + "-"*70)
        print(f"SUCCESS RATE: {success_count}/{total_tests} tests passed ({success_count/total_tests*100:.0f}%)")
        print("-"*70)
        
        return success_count >= 4  # Pass if at least 4 out of 5 tests succeed
        
    except Exception as e:
        print(f"✗ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_job_search():
    """Test job search with multiple APIs"""
    print("\n" + "="*70)
    print("TEST 3: JOB SEARCH API")
    print("="*70)
    
    test_skills = ["Python", "Django", "React"]
    print(f"\n✓ Searching jobs for skills: {', '.join(test_skills)}")
    print("  This may take 15-30 seconds as we query multiple APIs...\n")
    
    try:
        jobs = fetch_jobs_for_skills(test_skills, location="in", max_results=10)
        
        if jobs and len(jobs) > 0:
            print(f"✓ SUCCESS: Found {len(jobs)} jobs")
            print("\n" + "-"*70)
            print("SAMPLE JOBS:")
            print("-"*70)
            
            for i, job in enumerate(jobs[:3], 1):
                print(f"\n{i}. {job.get('title', 'N/A')}")
                print(f"   Company: {job.get('company', 'N/A')}")
                print(f"   Location: {job.get('location', 'N/A')}")
                print(f"   Source: {job.get('source', 'N/A')}")
                print(f"   URL: {job.get('url', 'N/A')[:60]}...")
            
            print("\n" + "-"*70)
            return True
        else:
            print("⚠ WARNING: No jobs found")
            print("  This might be normal if:")
            print("  - APIs are rate-limited")
            print("  - Network connection issues")
            print("  - No matching jobs available")
            print("  - API keys not configured (optional)")
            return None
            
    except Exception as e:
        print(f"✗ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("PLACEMENT PARTNER - FIX VERIFICATION TESTS")
    print("="*70)
    print("\nThis script will test:")
    print("1. PDF Text Extraction (with PyPDF2 fallback)")
    print("2. Resume Parsing (Name, Email, Phone, Skills)")
    print("3. Job Search API (Multiple sources)")
    print("\n" + "="*70)
    
    results = []
    
    # Test 1: PDF Extraction
    result1 = test_pdf_extraction()
    results.append(("PDF Extraction", result1))
    
    # Test 2: Resume Parsing
    result2 = test_resume_parsing()
    results.append(("Resume Parsing", result2))
    
    # Test 3: Job Search
    result3 = test_job_search()
    results.append(("Job Search API", result3))
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    for test_name, result in results:
        if result is True:
            status = "✓ PASSED"
        elif result is False:
            status = "✗ FAILED"
        else:
            status = "⚠ SKIPPED/WARNING"
        print(f"{test_name:20s} : {status}")
    
    print("="*70)
    
    passed = sum(1 for _, r in results if r is True)
    total = len(results)
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests PASSED! Your fixes are working correctly.")
    elif passed > 0:
        print("\n✓ Some tests passed. Review warnings/failures above.")
    else:
        print("\n⚠ Tests had issues. Review the errors above.")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
