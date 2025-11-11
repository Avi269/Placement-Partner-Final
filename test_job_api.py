"""
Test job search API integration
"""
from core.job_search import fetch_jobs_for_skills

print("=" * 60)
print("TESTING JOB SEARCH APIs")
print("=" * 60)

# Test skills
skills = ["Python", "Django", "React", "JavaScript", "SQL"]

print(f"\nSearching jobs for skills: {skills}")
print("This will take 5-10 seconds...\n")

try:
    jobs = fetch_jobs_for_skills(skills, max_results=5)
    
    print(f"\n✅ Found {len(jobs)} jobs!")
    print("=" * 60)
    
    for idx, job in enumerate(jobs, 1):
        print(f"\n{idx}. {job['title']}")
        print(f"   Company: {job['company']}")
        print(f"   Location: {job['location']}")
        print(f"   Source: {job['source']}")
        print(f"   URL: {job['url'][:80]}...")
        if job['salary_min']:
            print(f"   Salary: ${job['salary_min']} - ${job['salary_max']}")
    
    print("\n" + "=" * 60)
    print("✅ Job search API is working!")
    print("=" * 60)
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n")
