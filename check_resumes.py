"""
Check if resume exists in database
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'placement_partner.settings')
django.setup()

from core.models import Resume

print("=" * 60)
print("CHECKING RESUMES IN DATABASE")
print("=" * 60)

resumes = Resume.objects.all()
print(f"\nTotal resumes: {resumes.count()}")

if resumes.exists():
    print("\n📄 Resumes found:")
    for idx, resume in enumerate(resumes, 1):
        print(f"\n{idx}. Resume ID: {resume.id}")
        print(f"   Name: {resume.name or 'N/A'}")
        print(f"   Email: {resume.email or 'N/A'}")
        print(f"   Skills: {resume.extracted_skills or []}")
        print(f"   User: {resume.user or 'Anonymous'}")
        print(f"   Created: {resume.created_at}")
else:
    print("\n❌ No resumes found in database!")
    print("\n💡 Solution: Upload a resume first at http://127.0.0.1:8000/resume/")

print("\n" + "=" * 60)
