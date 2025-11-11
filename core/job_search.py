"""
Job Search API Integration
Fetches real-time jobs based on extracted skills
"""
import requests
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class JobSearchAPI:
    """Fetch jobs from multiple free APIs"""
    
    def __init__(self):
        # Adzuna API (Free tier: 1000 calls/month)
        self.adzuna_app_id = "test"  # Replace with your app_id from https://developer.adzuna.com/
        self.adzuna_api_key = "test"  # Replace with your API key
        
    def search_jobs_adzuna(self, skills: List[str], location: str = "us", max_results: int = 10) -> List[Dict]:
        """
        Search jobs using Adzuna API (FREE)
        Sign up: https://developer.adzuna.com/
        """
        try:
            # Build search query from skills
            query = " OR ".join(skills[:5])  # Use top 5 skills
            
            url = f"https://api.adzuna.com/v1/api/jobs/{location}/search/1"
            params = {
                "app_id": self.adzuna_app_id,
                "app_key": self.adzuna_api_key,
                "results_per_page": max_results,
                "what": query,
                "content-type": "application/json"
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                jobs = []
                
                for job in data.get("results", []):
                    jobs.append({
                        "title": job.get("title", ""),
                        "company": job.get("company", {}).get("display_name", "Unknown"),
                        "location": job.get("location", {}).get("display_name", "Remote"),
                        "description": job.get("description", "")[:500],  # First 500 chars
                        "url": job.get("redirect_url", ""),
                        "salary_min": job.get("salary_min"),
                        "salary_max": job.get("salary_max"),
                        "source": "Adzuna"
                    })
                
                logger.info(f"Found {len(jobs)} jobs from Adzuna")
                return jobs
            else:
                logger.error(f"Adzuna API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching from Adzuna: {e}")
            return []
    
    def search_jobs_remotive(self, skills: List[str], max_results: int = 10) -> List[Dict]:
        """
        Search remote jobs using Remotive API (FREE, no API key needed!)
        API: https://remotive.com/api/remote-jobs
        """
        try:
            url = "https://remotive.com/api/remote-jobs"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                all_jobs = data.get("jobs", [])
                
                # Filter jobs by skills
                matched_jobs = []
                skills_lower = [s.lower() for s in skills]
                
                for job in all_jobs:
                    job_title = job.get("title", "").lower()
                    job_desc = job.get("description", "").lower()
                    job_tags = " ".join(job.get("tags", [])).lower()
                    
                    # Check if any skill matches
                    if any(skill in job_title or skill in job_desc or skill in job_tags 
                           for skill in skills_lower):
                        matched_jobs.append({
                            "title": job.get("title", ""),
                            "company": job.get("company_name", "Unknown"),
                            "location": "Remote",
                            "description": job.get("description", "")[:500],
                            "url": job.get("url", ""),
                            "salary_min": None,
                            "salary_max": None,
                            "source": "Remotive"
                        })
                        
                        if len(matched_jobs) >= max_results:
                            break
                
                logger.info(f"Found {len(matched_jobs)} jobs from Remotive")
                return matched_jobs
            else:
                logger.error(f"Remotive API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching from Remotive: {e}")
            return []
    
    def search_jobs_github(self, skills: List[str], location: str = "", max_results: int = 10) -> List[Dict]:
        """
        Search jobs using GitHub Jobs API alternative (FREE)
        Using Arbeitnow API (no key needed)
        """
        try:
            url = "https://www.arbeitnow.com/api/job-board-api"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                all_jobs = data.get("data", [])
                
                # Filter by skills
                matched_jobs = []
                skills_lower = [s.lower() for s in skills]
                
                for job in all_jobs:
                    job_title = job.get("title", "").lower()
                    job_desc = job.get("description", "").lower()
                    job_tags = " ".join(job.get("tags", [])).lower()
                    
                    if any(skill in job_title or skill in job_desc or skill in job_tags 
                           for skill in skills_lower):
                        matched_jobs.append({
                            "title": job.get("title", ""),
                            "company": job.get("company_name", "Unknown"),
                            "location": job.get("location", "Remote"),
                            "description": job.get("description", "")[:500],
                            "url": job.get("url", ""),
                            "salary_min": None,
                            "salary_max": None,
                            "source": "Arbeitnow"
                        })
                        
                        if len(matched_jobs) >= max_results:
                            break
                
                logger.info(f"Found {len(matched_jobs)} jobs from Arbeitnow")
                return matched_jobs
            else:
                logger.error(f"Arbeitnow API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching from Arbeitnow: {e}")
            return []
    
    def search_all_sources(self, skills: List[str], location: str = "us", max_results: int = 20) -> List[Dict]:
        """
        Search jobs from all available sources
        Returns combined list of jobs
        """
        all_jobs = []
        
        # Try Remotive (most reliable, no API key)
        try:
            remotive_jobs = self.search_jobs_remotive(skills, max_results // 2)
            all_jobs.extend(remotive_jobs)
        except:
            pass
        
        # Try Arbeitnow
        try:
            arbeitnow_jobs = self.search_jobs_github(skills, location, max_results // 2)
            all_jobs.extend(arbeitnow_jobs)
        except:
            pass
        
        # Try Adzuna (requires API key)
        # Uncomment if you have API keys
        # try:
        #     adzuna_jobs = self.search_jobs_adzuna(skills, location, max_results // 3)
        #     all_jobs.extend(adzuna_jobs)
        # except:
        #     pass
        
        # Remove duplicates by URL
        seen_urls = set()
        unique_jobs = []
        for job in all_jobs:
            if job["url"] not in seen_urls:
                seen_urls.add(job["url"])
                unique_jobs.append(job)
        
        logger.info(f"Total unique jobs found: {len(unique_jobs)}")
        return unique_jobs[:max_results]


# Global instance
job_search_api = JobSearchAPI()


def fetch_jobs_for_skills(skills: List[str], location: str = "us", max_results: int = 20) -> List[Dict]:
    """
    Fetch jobs matching the given skills
    
    Args:
        skills: List of skills to search for
        location: Location code (us, uk, de, etc.)
        max_results: Maximum number of jobs to return
    
    Returns:
        List of job dictionaries
    """
    return job_search_api.search_all_sources(skills, location, max_results)
