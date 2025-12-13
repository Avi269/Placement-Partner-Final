"""Test Adzuna API Integration"""
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

print('=' * 60)
print('TESTING ADZUNA API INTEGRATION')
print('=' * 60)
print('\nSearching for Python Django jobs in India...\n')

jobs = fetch_jobs_for_skills(['python', 'django'], location='in', max_results=5)

if jobs:
    print(f'✅ SUCCESS! Found {len(jobs)} jobs\n')
    print('-' * 60)
    for i, job in enumerate(jobs[:3], 1):
        print(f'\n{i}. {job.get("title", "N/A")}')
        print(f'   Company: {job.get("company", "N/A")}')
        print(f'   Location: {job.get("location", "N/A")}')
        print(f'   Source: {job.get("source", "N/A")}')
        if job.get("salary_min"):
            print(f'   Salary: ₹{job.get("salary_min"):,} - ₹{job.get("salary_max"):,}')
else:
    print('⚠️  No jobs found')
    
print('\n' + '=' * 60)
print('Adzuna API is now active in your project!')
print('=' * 60)
