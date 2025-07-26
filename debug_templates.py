#!/usr/bin/env python3
"""
Debug script to test template rendering
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'placement_partner.settings')
django.setup()

from django.test import RequestFactory
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from core.views import home, resume_upload_view, job_matching_view, cover_letter_view, offer_analysis_view

def test_template_rendering():
    """Test template rendering for each view"""
    print("🔍 Testing Template Rendering")
    print("=" * 50)
    
    # Create a request factory
    factory = RequestFactory()
    
    # Test each view
    views = [
        ("Home", home),
        ("Resume Upload", resume_upload_view),
        ("Job Matching", job_matching_view),
        ("Cover Letter", cover_letter_view),
        ("Offer Analysis", offer_analysis_view),
    ]
    
    for view_name, view_func in views:
        try:
            # Create a request
            request = factory.get('/')
            
            # Call the view
            response = view_func(request)
            
            if response.status_code == 200:
                print(f"✅ {view_name}: Success (Status: {response.status_code})")
                print(f"   📍 Content Length: {len(response.content)} bytes")
            else:
                print(f"❌ {view_name}: Status {response.status_code}")
                if hasattr(response, 'content'):
                    print(f"   📍 Error: {response.content.decode()[:200]}...")
                    
        except Exception as e:
            print(f"❌ {view_name}: Exception - {str(e)}")
            import traceback
            traceback.print_exc()
    
    print()

def test_static_files():
    """Test static file loading"""
    print("🎨 Testing Static File Loading")
    print("=" * 50)
    
    try:
        # Test if static files can be loaded
        from django.conf import settings
        from django.contrib.staticfiles.finders import find
        
        static_files = [
            'css/style.css',
            'js/main.js'
        ]
        
        for file_path in static_files:
            try:
                found_path = find(file_path)
                if found_path:
                    print(f"✅ {file_path}: Found at {found_path}")
                else:
                    print(f"❌ {file_path}: Not found")
            except Exception as e:
                print(f"❌ {file_path}: Error - {str(e)}")
                
    except Exception as e:
        print(f"❌ Static files test failed: {str(e)}")
    
    print()

def test_url_patterns():
    """Test URL patterns"""
    print("🔗 Testing URL Patterns")
    print("=" * 50)
    
    try:
        from django.urls import reverse
        from django.urls.exceptions import NoReverseMatch
        
        urls = [
            'home',
            'resume_upload',
            'job_matching',
            'cover_letter',
            'offer_analysis',
            'api-root'
        ]
        
        for url_name in urls:
            try:
                url = reverse(url_name)
                print(f"✅ {url_name}: {url}")
            except NoReverseMatch:
                print(f"❌ {url_name}: No reverse match found")
            except Exception as e:
                print(f"❌ {url_name}: Error - {str(e)}")
                
    except Exception as e:
        print(f"❌ URL patterns test failed: {str(e)}")
    
    print()

def main():
    """Run all debug tests"""
    print("🚀 PLACEMENT PARTNER - TEMPLATE DEBUG TEST")
    print("=" * 60)
    print(f"Django Version: {django.get_version()}")
    print(f"Python Version: {sys.version}")
    print()
    
    test_url_patterns()
    test_static_files()
    test_template_rendering()
    
    print("🎯 Debug test completed!")

if __name__ == "__main__":
    main() 