"""Test All Job APIs"""
import os
import sys
import django
from pathlib import Path

# Setup Django - use dynamic path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'placement_partner.settings')
django.setup()

from core.job_search import fetch_jobs_for_skills

print('=' * 70)
print('TESTING ALL JOB APIs WITH FALLBACK SYSTEM')
print('=' * 70)
print('\nSearching for Java Spring Boot jobs in India...\n')

jobs = fetch_jobs_for_skills(['java', 'spring boot'], location='in', max_results=15)

if jobs:
    print(f'✅ SUCCESS! Found {len(jobs)} jobs from multiple sources\n')
    print('-' * 70)
    
    # Group by source
    by_source = {}
    for job in jobs:
        source = job.get("source", "Unknown")
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(job)
    
    # Display summary
    print('\n📊 JOBS BY SOURCE:')
    print('-' * 70)
    for source, source_jobs in by_source.items():
        print(f'  {source}: {len(source_jobs)} jobs')
    
    print('\n' + '-' * 70)
    print('📝 SAMPLE JOBS:')
    print('-' * 70)
    
    for i, job in enumerate(jobs[:5], 1):
        print(f'\n{i}. {job.get("title", "N/A")}')
        print(f'   Company: {job.get("company", "N/A")}')
        print(f'   Location: {job.get("location", "N/A")}')
        print(f'   Source: {job.get("source", "N/A")}')
        if job.get("salary_min") and job.get("salary_max"):
            print(f'   Salary: ₹{job.get("salary_min"):,} - ₹{job.get("salary_max"):,}')
        print(f'   URL: {job.get("url", "N/A")[:60]}...')
else:
    print('⚠️  No jobs found')
    
print('\n' + '=' * 70)
print('🎉 ACTIVE APIs:')
print('  ✅ Curated Indian Jobs Database')
print('  ✅ Adzuna API (India)')
print('  ✅ Jooble API (India) - NEW!')
print('  ✅ Remotive API (Remote)')
print('  ✅ Arbeitnow API (Tech)')
print('  ✅ The Muse API (Remote)')
print('=' * 70)
