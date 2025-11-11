"""
Test script to verify resume processing fixes
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'placement_partner.settings')
django.setup()

from core.utils import (
    parse_resume_file, 
    extract_text_from_file, 
    extract_skills_from_text,
    enrich_parsed_resume
)
from django.core.exceptions import ValidationError
import tempfile

def test_text_parsing():
    """Test parsing resume from plain text"""
    print("\n=== Testing Text Parsing ===")
    
    sample_text = """
    John Doe
    john.doe@email.com
    +1234567890
    
    Education:
    Bachelor of Technology in Computer Science
    XYZ University, 2020-2024
    
    Experience:
    Software Developer at ABC Corp
    - Developed web applications using Django and React
    - Worked on machine learning models
    
    Skills:
    Python, Django, JavaScript, React, Machine Learning, SQL, AWS, Docker
    """
    
    try:
        # Create temp file with text
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
            f.write(sample_text)
            temp_path = f.name
        
        # Test skill extraction
        skills = extract_skills_from_text(sample_text)
        print(f"✓ Extracted skills: {skills[:5]}...")
        
        # Test enrich function
        data = {"parsed_text": sample_text}
        enriched = enrich_parsed_resume(data)
        print(f"✓ Enriched data - Name: {enriched.get('name')}, Email: {enriched.get('email')}")
        
        # Clean up
        os.remove(temp_path)
        
        print("✓ Text parsing test PASSED")
        return True
    except Exception as e:
        print(f"✗ Text parsing test FAILED: {e}")
        return False

def test_error_handling():
    """Test error handling for invalid files"""
    print("\n=== Testing Error Handling ===")
    
    try:
        # Test with non-existent file
        try:
            extract_text_from_file("/nonexistent/file.pdf")
            print("✗ Should have raised ValidationError for non-existent file")
            return False
        except (ValidationError, Exception) as e:
            print(f"✓ Correctly raised error for non-existent file")
        
        # Test with invalid file type
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
            f.write(b"test content")
            temp_path = f.name
        
        try:
            extract_text_from_file(temp_path)
            print("✗ Should have raised ValidationError for invalid file type")
            os.remove(temp_path)
            return False
        except ValidationError as e:
            print(f"✓ Correctly raised error for invalid file type: {str(e)[:50]}...")
            os.remove(temp_path)
        
        print("✓ Error handling test PASSED")
        return True
    except Exception as e:
        print(f"✗ Error handling test FAILED: {e}")
        return False

def test_utils_imports():
    """Test that all required utilities are importable"""
    print("\n=== Testing Utility Imports ===")
    
    try:
        from core.utils import (
            generate_cover_letter_with_gemini,
            analyze_offer_letter_with_gemini,
            calculate_job_fit_with_gemini,
            get_learning_resources_with_gemini,
            optimize_resume_for_ats,
            validate_file_type,
            validate_file_size,
            sanitize_filename
        )
        print("✓ All utility functions imported successfully")
        
        # Test sanitize filename
        clean = sanitize_filename("../../malicious/path/../file.pdf")
        print(f"✓ Sanitize filename works: '{clean}'")
        
        print("✓ Utility imports test PASSED")
        return True
    except Exception as e:
        print(f"✗ Utility imports test FAILED: {e}")
        return False

def test_dependencies():
    """Test that all required dependencies are installed"""
    print("\n=== Testing Dependencies ===")
    
    dependencies = [
        ('spacy', 'spaCy'),
        ('docx2txt', 'docx2txt'),
        ('pdfminer', 'pdfminer.six'),
        ('google.generativeai', 'google-generativeai'),
        ('pytesseract', 'pytesseract'),
        ('pdf2image', 'pdf2image'),
    ]
    
    all_ok = True
    for module_name, package_name in dependencies:
        try:
            __import__(module_name)
            print(f"✓ {package_name} installed")
        except ImportError:
            print(f"✗ {package_name} NOT installed")
            all_ok = False
    
    if all_ok:
        print("✓ All dependencies test PASSED")
    else:
        print("✗ Some dependencies missing")
    
    return all_ok

def test_model_structure():
    """Test that Resume model has all required fields"""
    print("\n=== Testing Model Structure ===")
    
    try:
        from core.models import Resume
        
        required_fields = [
            'user', 'file', 'parsed_text', 'extracted_skills',
            'education', 'experience', 'name', 'email', 'phone'
        ]
        
        model_fields = [f.name for f in Resume._meta.get_fields()]
        
        for field in required_fields:
            if field in model_fields:
                print(f"✓ Resume.{field} exists")
            else:
                print(f"✗ Resume.{field} missing")
                return False
        
        print("✓ Model structure test PASSED")
        return True
    except Exception as e:
        print(f"✗ Model structure test FAILED: {e}")
        return False

def run_all_tests():
    """Run all tests and report results"""
    print("=" * 60)
    print("RESUME PROCESSING FIX VERIFICATION")
    print("=" * 60)
    
    tests = [
        test_dependencies,
        test_utils_imports,
        test_model_structure,
        test_text_parsing,
        test_error_handling,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"\n✗ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✓✓✓ ALL TESTS PASSED! Resume processing is fixed. ✓✓✓")
    else:
        print(f"\n✗✗✗ {total - passed} test(s) failed. Please review above. ✗✗✗")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
