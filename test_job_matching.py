"""
Quick test script for job matching functionality
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'placement_partner.settings')
django.setup()

from core.utils import calculate_job_fit_with_gemini

# Test data
resume_skills = ["Python", "Django", "React", "JavaScript", "SQL", "Git"]
job_description = """
We are looking for a Senior Software Engineer.

Requirements:
- 5+ years of experience in software development
- Proficiency in Python, JavaScript, and React
- Experience with Django, AWS, and Docker
- Strong knowledge of SQL and database design
- Experience with CI/CD pipelines
"""

print("=" * 60)
print("TESTING JOB MATCHING")
print("=" * 60)
print(f"\nResume Skills: {resume_skills}")
print(f"\nJob Description: {job_description[:100]}...")

try:
    print("\n🔍 Calling calculate_job_fit_with_gemini...")
    fit_score, matching_skills, missing_skills = calculate_job_fit_with_gemini(
        resume_skills,
        job_description
    )
    
    print("\n" + "=" * 60)
    print("✅ SUCCESS! Results:")
    print("=" * 60)
    print(f"\n📊 Fit Score: {fit_score}%")
    print(f"\n✅ Matching Skills ({len(matching_skills)}):")
    for skill in matching_skills:
        print(f"   • {skill}")
    
    print(f"\n⚠️  Missing Skills ({len(missing_skills)}):")
    for skill in missing_skills:
        print(f"   • {skill}")
    
    print("\n" + "=" * 60)
    print("✅ Job matching is working correctly!")
    print("=" * 60)

except Exception as e:
    print("\n" + "=" * 60)
    print("❌ ERROR!")
    print("=" * 60)
    print(f"\nError: {str(e)}")
    import traceback
    traceback.print_exc()
    print("\n" + "=" * 60)
