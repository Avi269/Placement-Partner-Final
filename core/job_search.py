"""
============================================================================
JOB SEARCH API INTEGRATION - OPTIMIZED VERSION
============================================================================
Fetches real-time job postings from 3 reliable APIs:
1. Remotive API (FREE, no key) - Remote tech jobs
2. Arbeitnow API (FREE, no key) - International jobs  
3. Adzuna API (Optional) - India-specific jobs (needs key)

All other APIs removed for simplicity and maintainability.
============================================================================
"""

import requests
import logging
from typing import List, Dict
import os
import re

logger = logging.getLogger(__name__)

def strip_html_tags(text):
    """Remove HTML tags from text"""
    if not text:
        return ""
    # Remove HTML tags
    clean = re.compile('<.*?>')
    text = re.sub(clean, '', text)
    # Remove extra whitespace
    text = ' '.join(text.split())
    return text

class JobSearchAPI:
    """Simplified job search with only 3 reliable APIs"""
    
    def __init__(self):
        """Initialize with optional Adzuna credentials"""
        self.adzuna_app_id = os.getenv("ADZUNA_APP_ID", "")
        self.adzuna_api_key = os.getenv("ADZUNA_API_KEY", "")
        
        if self.adzuna_app_id and self.adzuna_api_key:
            logger.info("JobSearchAPI: Adzuna enabled")
        else:
            logger.info("JobSearchAPI: Using free APIs only (Remotive + Arbeitnow)")
    
    def search_jobs(self, skills: List[str], location: str = "in", max_results: int = 15) -> List[Dict]:
        """
        Search for jobs using multiple APIs with automatic failover
        
        Args:
            skills: List of skills to search for
            location: Location code ("in" for India)
            max_results: Maximum number of jobs to return
        
        Returns:
            List of job dictionaries
        """
        if not skills or not isinstance(skills, list):
            logger.warning("No valid skills provided")
            return []
        
        all_jobs = []
        
        # 1. Remotive API (FREE, no key, reliable)
        try:
            remotive_jobs = self._fetch_remotive(skills, max_results=5)
            if remotive_jobs:
                all_jobs.extend(remotive_jobs)
                logger.info(f"Remotive API: {len(remotive_jobs)} jobs fetched")
        except Exception as e:
            logger.error(f"Remotive API failed: {e}")
        
        # 2. Arbeitnow API (FREE, no key, reliable)
        try:
            arbeitnow_jobs = self._fetch_arbeitnow(skills, max_results=5)
            if arbeitnow_jobs:
                all_jobs.extend(arbeitnow_jobs)
                logger.info(f"Arbeitnow API: {len(arbeitnow_jobs)} jobs fetched")
        except Exception as e:
            logger.error(f"Arbeitnow API failed: {e}")
        
        # 3. Adzuna API (Optional, best for India)
        if self.adzuna_app_id and self.adzuna_api_key and location == "in":
            try:
                adzuna_jobs = self._fetch_adzuna(skills, max_results=5)
                if adzuna_jobs:
                    all_jobs.extend(adzuna_jobs)
                    logger.info(f"Adzuna API: {len(adzuna_jobs)} jobs fetched")
            except Exception as e:
                logger.error(f"Adzuna API failed: {e}")
        
        if not all_jobs:
            logger.warning(f"No jobs found for skills: {', '.join(skills)}")
            return []
        
        # Remove duplicates
        unique_jobs = self._deduplicate_jobs(all_jobs)
        
        # Sort by relevance (India priority)
        sorted_jobs = self._sort_by_relevance(unique_jobs, skills, location)
        
        logger.info(f"Total unique jobs: {len(sorted_jobs)}")
        return sorted_jobs[:max_results]
    
    def _fetch_remotive(self, skills: List[str], max_results: int = 10) -> List[Dict]:
        """Fetch from Remotive API"""
        url = "https://remotive.com/api/remote-jobs"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            return []
        
        all_jobs = response.json().get("jobs", [])
        
        # Filter by technical skills (not generic terms)
        generic_terms = {'api', 'rest', 'css', 'html', 'git'}
        tech_skills = [s.lower() for s in skills if s.lower() not in generic_terms]
        
        matched_jobs = []
        for job in all_jobs:
            title = job.get("title", "").lower()
            desc = job.get("description", "").lower()
            tags = " ".join(job.get("tags", [])).lower()
            
            # Require at least 1 technical skill match
            if any(skill in f"{title} {desc} {tags}" for skill in tech_skills):
                matched_jobs.append({
                    "title": job.get("title", ""),
                    "company": job.get("company_name", "Unknown"),
                    "location": "Remote (India-friendly)",
                    "description": strip_html_tags(job.get("description", ""))[:500],  # Clean HTML
                    "url": job.get("url", ""),
                    "salary_min": None,
                    "salary_max": None,
                    "source": "Remotive",
                    "skills": job.get("tags", [])[:5]
                })
                
                if len(matched_jobs) >= max_results:
                    break
        
        return matched_jobs
    
    def _fetch_arbeitnow(self, skills: List[str], max_results: int = 10) -> List[Dict]:
        """Fetch from Arbeitnow API"""
        url = "https://www.arbeitnow.com/api/job-board-api"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            return []
        
        all_jobs = response.json().get("data", [])
        
        # Filter by technical skills
        generic_terms = {'api', 'rest', 'css', 'html', 'git'}
        tech_skills = [s.lower() for s in skills if s.lower() not in generic_terms]
        
        matched_jobs = []
        for job in all_jobs:
            title = job.get("title", "").lower()
            desc = job.get("description", "").lower()
            tags = " ".join(job.get("tags", [])).lower()
            
            if any(skill in f"{title} {desc} {tags}" for skill in tech_skills):
                location = job.get("location", "Remote")
                
                matched_jobs.append({
                    "title": job.get("title", ""),
                    "company": job.get("company_name", "Unknown"),
                    "location": location,
                    "description": strip_html_tags(job.get("description", ""))[:500],  # Clean HTML
                    "url": job.get("url", ""),
                    "salary_min": None,
                    "salary_max": None,
                    "source": "Arbeitnow",
                    "skills": job.get("tags", [])[:5]
                })
                
                if len(matched_jobs) >= max_results:
                    break
        
        return matched_jobs
    
    def _fetch_adzuna(self, skills: List[str], max_results: int = 10) -> List[Dict]:
        """Fetch from Adzuna API (India-specific)"""
        # Use top 5 technical skills
        generic_terms = {'api', 'rest', 'css', 'html', 'git'}
        tech_skills = [s for s in skills if s.lower() not in generic_terms]
        query = " OR ".join(tech_skills[:5])
        
        url = f"https://api.adzuna.com/v1/api/jobs/in/search/1"
        params = {
            "app_id": self.adzuna_app_id,
            "app_key": self.adzuna_api_key,
            "results_per_page": max_results,
            "what": query,
            "where": "India",
            "content-type": "application/json"
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        jobs = []
        
        for job in data.get("results", []):
            jobs.append({
                "title": job.get("title", ""),
                "company": job.get("company", {}).get("display_name", "Unknown"),
                "location": job.get("location", {}).get("display_name", "India"),
                "description": strip_html_tags(job.get("description", ""))[:500],  # Clean HTML
                "url": job.get("redirect_url", ""),
                "salary_min": job.get("salary_min"),
                "salary_max": job.get("salary_max"),
                "source": "Adzuna",
                "skills": []
            })
        
        return jobs
    
    def _deduplicate_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """Remove duplicate jobs based on title + company"""
        seen = set()
        unique = []
        
        for job in jobs:
            key = f"{job.get('title', '').lower()}_{job.get('company', '').lower()}"
            if key not in seen:
                seen.add(key)
                unique.append(job)
        
        return unique
    
    def _sort_by_relevance(self, jobs: List[Dict], skills: List[str], location: str) -> List[Dict]:
        """Sort jobs by relevance with India priority"""
        skills_lower = set(s.lower() for s in skills)
        
        def calc_score(job):
            title = job.get('title', '').lower()
            desc = job.get('description', '').lower()
            loc = job.get('location', '').lower()
            combined = f"{title} {desc}"
            
            # Base score: skill matches
            skill_score = sum(1 for skill in skills_lower if skill in combined)
            
            # India priority bonus
            india_terms = ['india', 'mumbai', 'delhi', 'bangalore', 'bengaluru', 'hyderabad', 'chennai', 'pune']
            if any(term in loc for term in india_terms):
                return skill_score + 100  # High priority
            elif 'remote' in loc or 'worldwide' in loc:
                return skill_score + 50  # Medium priority
            
            return skill_score
        
        jobs.sort(key=calc_score, reverse=True)
        return jobs


# Global instance
_job_api = None

def get_job_api():
    """Get singleton instance"""
    global _job_api
    if _job_api is None:
        _job_api = JobSearchAPI()
    return _job_api

def fetch_jobs_for_skills(skills: List[str], location: str = "in", max_results: int = 15) -> List[Dict]:
    """
    Public function to fetch jobs
    
    Args:
        skills: List of skills to search for
        location: Location code ("in" for India)
        max_results: Maximum number of jobs
    
    Returns:
        List of job dictionaries
    """
    api = get_job_api()
    return api.search_jobs(skills, location, max_results)
