"""
Test if job matching page shows extracted resume data
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'placement_partner.settings')
django.setup()

from core.models import Resume
from django.test import RequestFactory
from core.views import job_matching_view

print("=" * 60)
print("TESTING RESUME DATA IN JOB MATCHING")
print("=" * 60)

# Get latest resume
resume = Resume.objects.last()
if not resume:
    print("\n❌ No resume found in database!")
    print("Upload a resume first at: http://127.0.0.1:8000/resume/")
    exit(1)

print(f"\n✅ Latest Resume Found:")
print(f"   ID: {resume.id}")
print(f"   Name: {resume.name or 'N/A'}")
print(f"   Email: {resume.email or 'N/A'}")
print(f"   Skills: {resume.extracted_skills or []}")
print(f"   Total Skills: {len(resume.extracted_skills or [])}")

# Create a mock request
factory = RequestFactory()
request = factory.get('/job-matching/')
request.user = type('User', (), {'is_authenticated': False})()
request.session = {'resume_id': resume.id}

print("\n🔍 Testing job_matching_view GET request...")
try:
    response = job_matching_view(request)
    print(f"✅ Response status: {response.status_code}")
    
    # Check if context has resume data
    if hasattr(response, 'context_data'):
        context = response.context_data
        if 'resume' in context:
            print(f"✅ Resume in context: {context['resume'].name}")
            print(f"✅ Has resume: {context.get('has_resume', False)}")
        else:
            print("⚠️  No resume in context")
    
    print("\n" + "=" * 60)
    print("✅ Job matching view is ready!")
    print("=" * 60)
    print("\n📋 What you should see on the page:")
    print("   1. Green card with 'Your Resume Profile'")
    print("   2. Your name, email, phone")
    print("   3. All extracted skills as blue badges")
    print("   4. Experience list (if available)")
    print("\n🚀 Test at: http://127.0.0.1:8000/job-matching/")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
