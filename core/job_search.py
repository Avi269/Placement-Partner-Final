"""
============================================================================
JOB SEARCH API INTEGRATION - 100% DYNAMIC
============================================================================
This module fetches REAL-TIME job postings from multiple live APIs based on
user skills extracted from resumes.

Features:
- NO hardcoded jobs - everything fetched dynamically
- Multiple free job APIs (no API key needed for most)
- Intelligent deduplication and relevance sorting
- Automatic failover between APIs

Job API Sources (All Dynamic):
1. Remotive API (FREE, no key needed)
   - Real-time remote tech jobs
   
2. Arbeitnow API (FREE, no key needed)
   - European and international jobs
   
3. Adzuna API (Optional): Free tier 1000 calls/month
   - India-specific jobs
   - Set: ADZUNA_APP_ID, ADZUNA_API_KEY in .env

4. Jooble API (Optional): Free tier 500 requests
   - Global job search
   - Set: JOOBLE_API_KEY in .env

5. JSearch/RapidAPI (Optional): 150 requests/month
   - Aggregates Indeed, LinkedIn, Glassdoor
   - Set: RAPIDAPI_KEY in .env

Usage:
    api = JobSearchAPI()
    jobs = api.search_indian_jobs(skills=['python', 'django'])
    # Returns live jobs from multiple APIs
============================================================================
"""

import requests  # For API calls
import logging  # For error logging
from typing import List, Dict  # Type hints

# Configure logging
logger = logging.getLogger(__name__)

# ============================================================================
# JOB SEARCH CLASS
# ============================================================================

class JobSearchAPI:
    """
    Fetch job postings based on user skills
    
    Provides curated Indian tech jobs and can integrate with external APIs
    like Adzuna for additional job sources.
    """
    
    def __init__(self):
        """Initialize job search API with credentials from environment variables"""
        import os
        
        # === ADZUNA API CREDENTIALS ===
        # Get free API key from: https://developer.adzuna.com/
        # Free tier: 1000 API calls per month
        # Set in .env: ADZUNA_APP_ID and ADZUNA_API_KEY
        self.adzuna_app_id = os.getenv("ADZUNA_APP_ID", "")
        self.adzuna_api_key = os.getenv("ADZUNA_API_KEY", "")
        
        # === RAPIDAPI JSEARCH (Multi-source aggregator) ===
        # Aggregates from Indeed, LinkedIn, Glassdoor, ZipRecruiter
        # Sign up: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
        # Free tier: 150 requests/month
        # Set in .env: RAPIDAPI_KEY
        self.rapidapi_key = os.getenv("RAPIDAPI_KEY", "")
        self.rapidapi_host = "jsearch.p.rapidapi.com"
        
        # === THE MUSE API ===
        # Free job postings, no API key required
        # Docs: https://www.themuse.com/developers/api/v2
        # No rate limit on free tier
        
        # === JOOBLE API ===
        # Free tier: 500 requests (contact for increase)
        # Sign up: https://jooble.org/api/about
        # Set in .env: JOOBLE_API_KEY
        self.jooble_api_key = os.getenv("JOOBLE_API_KEY", "")
        
        logger.info("JobSearchAPI initialized - All jobs will be fetched dynamically from live APIs")
    
    def search_indian_jobs(self, skills: List[str], location: str = "India", max_results: int = 15) -> List[Dict]:
        """
        Search for jobs in India using multiple APIs dynamically
        NO hardcoded jobs - all fetched from live APIs
        """
        try:
            all_jobs = []
            
            # Validate skills input
            if not skills or not isinstance(skills, list) or len(skills) == 0:
                logger.warning("No skills provided for job search")
                return []
            
            # Try multiple APIs to get diverse results
            logger.info(f"Searching for jobs with skills: {', '.join(skills)} in {location}")
            
            # 1. Try Remotive (Free, no API key) - with timeout
            try:
                remotive_jobs = self.search_jobs_remotive(skills, max_results=5)
                if remotive_jobs:
                    all_jobs.extend(remotive_jobs)
                    logger.info(f"Got {len(remotive_jobs)} jobs from Remotive")
                else:
                    logger.info("No jobs found from Remotive")
            except requests.Timeout:
                logger.error("Remotive API timeout - taking too long to respond")
            except requests.RequestException as e:
                logger.error(f"Remotive API connection error: {e}")
            except Exception as e:
                logger.error(f"Remotive API failed: {e}")
            
            # 2. Try Arbeitnow (Free, no API key)
            try:
                arbeitnow_jobs = self.search_jobs_github(skills, location, max_results=5)
                if arbeitnow_jobs:
                    all_jobs.extend(arbeitnow_jobs)
                    logger.info(f"Got {len(arbeitnow_jobs)} jobs from Arbeitnow")
                else:
                    logger.info("No jobs found from Arbeitnow")
            except requests.Timeout:
                logger.error("Arbeitnow API timeout")
            except requests.RequestException as e:
                logger.error(f"Arbeitnow API connection error: {e}")
            except Exception as e:
                logger.error(f"Arbeitnow API failed: {e}")
            
            # 3. Try Adzuna if configured
            if self.adzuna_app_id and self.adzuna_api_key:
                try:
                    adzuna_jobs = self.search_jobs_adzuna(skills, "in", max_results=5)
                    if adzuna_jobs:
                        all_jobs.extend(adzuna_jobs)
                        logger.info(f"Got {len(adzuna_jobs)} jobs from Adzuna")
                    else:
                        logger.info("No jobs found from Adzuna")
                except requests.Timeout:
                    logger.error("Adzuna API timeout")
                except requests.RequestException as e:
                    logger.error(f"Adzuna API connection error: {e}")
                except Exception as e:
                    logger.error(f"Adzuna API failed: {e}")
            else:
                logger.info("Adzuna API not configured (set ADZUNA_APP_ID and ADZUNA_API_KEY in .env)")
            
            # 4. Try Jooble if configured
            if self.jooble_api_key:
                try:
                    jooble_jobs = self.search_jobs_jooble(skills, location, max_results=5)
                    if jooble_jobs:
                        all_jobs.extend(jooble_jobs)
                        logger.info(f"Got {len(jooble_jobs)} jobs from Jooble")
                    else:
                        logger.info("No jobs found from Jooble")
                except requests.Timeout:
                    logger.error("Jooble API timeout")
                except requests.RequestException as e:
                    logger.error(f"Jooble API connection error: {e}")
                except Exception as e:
                    logger.error(f"Jooble API failed: {e}")
            else:
                logger.info("Jooble API not configured (set JOOBLE_API_KEY in .env)")
            
            # If no jobs found, log helpful message
            if not all_jobs:
                logger.warning(f"No jobs found for skills: {', '.join(skills)}")
                logger.info("Try: 1) Broadening your skills, 2) Configuring more API keys, 3) Checking your internet connection")
                return []
            
            # Remove duplicates based on title + company
            seen = set()
            unique_jobs = []
            for job in all_jobs:
                key = f"{job.get('title', '').lower()}_{job.get('company', '').lower()}"
                if key not in seen:
                    seen.add(key)
                    unique_jobs.append(job)
            
            # Sort by relevance with INDIA PRIORITY
            skills_lower = set([s.lower() for s in skills])
            
            def calc_relevance(job):
                title = job.get('title', '').lower()
                desc = job.get('description', '').lower()
                company = job.get('company', '').lower()
                location = job.get('location', '').lower()
                combined = f"{title} {desc} {company}"
                
                # Base score: skill matches
                skill_score = sum(1 for skill in skills_lower if skill in combined)
                
                # INDIA PRIORITY: Add 100 points for India jobs
                india_bonus = 0
                if any(india_term in location for india_term in ['india', 'indian', 'mumbai', 'delhi', 'bangalore', 'bengaluru', 'hyderabad', 'chennai', 'pune', 'kolkata']):
                    india_bonus = 100
                
                # REMOTE jobs that allow India: Add 50 points
                elif 'remote' in location or 'worldwide' in location:
                    india_bonus = 50
                
                return skill_score + india_bonus
            
            unique_jobs.sort(key=calc_relevance, reverse=True)
            
            result = unique_jobs[:max_results]
            logger.info(f"Returning {len(result)} unique jobs after deduplication")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in search_indian_jobs: {e}")
            return []
    
    def search_jobs_adzuna(self, skills: List[str], location: str = "in", max_results: int = 10) -> List[Dict]:
        """
        Search jobs using Adzuna API (FREE)
        Sign up: https://developer.adzuna.com/
        INDIA-FOCUSED: location="in" searches India-specific jobs
        """
        try:
            # Build search query from technical skills only
            very_generic = {'api', 'rest', 'css', 'html', 'git', 'github'}
            technical_skills = [s for s in skills if s.lower() not in very_generic]
            query = " OR ".join(technical_skills[:5])  # Use top 5 technical skills
            
            # Force India location
            url = f"https://api.adzuna.com/v1/api/jobs/in/search/1"  # 'in' = India
            params = {
                "app_id": self.adzuna_app_id,
                "app_key": self.adzuna_api_key,
                "results_per_page": max_results,
                "what": query,
                "where": "India",  # Explicitly search in India
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
            response = requests.get(url, timeout=15)  # Increased timeout
            
            if response.status_code == 200:
                data = response.json()
                all_jobs = data.get("jobs", [])
                
                if not all_jobs:
                    logger.warning("Remotive API returned no jobs")
                    return []
                
                # Filter jobs by skills with VERY strict matching
                matched_jobs = []
                skills_lower = [s.lower() for s in skills if s]  # Filter empty skills
                
                # Define truly generic terms that appear in almost any job
                very_generic = {'api', 'rest', 'css', 'html', 'git', 'github'}
                # Core technical skills that indicate specific roles
                technical_skills = [s for s in skills_lower if s not in very_generic]
                
                if not technical_skills:
                    logger.warning("Only generic skills provided, results may be broad")
                    technical_skills = skills_lower  # Use all skills if none are technical
                
                for job in all_jobs:
                    job_title = job.get("title", "").lower()
                    job_desc = job.get("description", "").lower()
                    job_tags = " ".join(job.get("tags", [])).lower()
                    job_location = job.get("candidate_required_location", "")
                    
                    # STRICT: Require at least 1 technical skill match in title OR 2 in description
                    title_matches = sum(1 for skill in technical_skills if skill in job_title)
                    desc_matches = sum(1 for skill in technical_skills if skill in job_desc)
                    tag_matches = sum(1 for skill in technical_skills if skill in job_tags)
                    
                    # Must have strong technical skill match - not just generic terms
                    if title_matches >= 1 or desc_matches >= 2 or tag_matches >= 2:
                        # Check if job is available for India
                        location_text = f"{job_location} {job_desc}".lower()
                        is_india_friendly = (
                            'india' in location_text or 
                            'worldwide' in location_text or 
                            'anywhere' in location_text or
                            not job_location  # No location restriction
                        )
                        
                        # Prefer India-friendly jobs
                        display_location = "Remote (India)" if is_india_friendly else "Remote"
                        
                        matched_jobs.append({
                            "title": job.get("title", ""),
                            "company": job.get("company_name", "Unknown"),
                            "location": display_location,
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
                logger.error(f"Remotive API error: {response.status_code} - {response.text[:200]}")
                return []
                
        except requests.Timeout:
            logger.error("Remotive API request timed out")
            return []
        except requests.RequestException as e:
            logger.error(f"Remotive API network error: {e}")
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
                
                # Filter by skills with stricter matching
                matched_jobs = []
                skills_lower = [s.lower() for s in skills]
                
                # Define very generic terms
                very_generic = {'html', 'css', 'javascript', 'git', 'rest', 'api', 'rest api'}
                technical_skills = [s for s in skills_lower if s not in very_generic]
                
                for job in all_jobs:
                    job_title = job.get("title", "").lower()
                    job_desc = job.get("description", "").lower()
                    job_tags = " ".join(job.get("tags", [])).lower()
                    job_location = job.get("location", "Remote")
                    
                    # Count technical skill matches
                    tech_matches = sum(1 for skill in technical_skills 
                                      if skill in job_title or skill in job_desc or skill in job_tags)
                    
                    # Require at least 1 technical skill match
                    if tech_matches >= 1:
                        location_lower = job_location.lower()
                        
                        # Prioritize India jobs
                        is_india = any(term in location_lower for term in 
                                      ['india', 'mumbai', 'delhi', 'bangalore', 'bengaluru', 'hyderabad', 'chennai', 'pune'])
                        
                        # Label remote jobs
                        if is_india:
                            display_loc = job_location
                        elif 'remote' in location_lower:
                            display_loc = f"{job_location} (India-friendly)"
                        else:
                            display_loc = job_location
                        
                        matched_jobs.append({
                            "title": job.get("title", ""),
                            "company": job.get("company_name", "Unknown"),
                            "location": display_loc,
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
    
    def search_jobs_jsearch(self, skills: List[str], location: str = "in", max_results: int = 10) -> List[Dict]:
        """
        Search jobs using JSearch API via RapidAPI (Aggregates Indeed, LinkedIn, Glassdoor, ZipRecruiter)
        Sign up: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
        Free tier: 150 requests/month
        """
        try:
            # Check if API key is configured
            if self.rapidapi_key == "PASTE_YOUR_RAPIDAPI_KEY_HERE":
                logger.info("JSearch API key not configured, skipping")
                return []
            
            # Build search query
            query = " ".join(skills[:3])  # Use top 3 skills
            
            # Map location codes
            location_map = {
                "in": "India",
                "us": "United States",
                "uk": "United Kingdom"
            }
            location_name = location_map.get(location, "India")
            
            url = "https://jsearch.p.rapidapi.com/search"
            headers = {
                "X-RapidAPI-Key": self.rapidapi_key,
                "X-RapidAPI-Host": self.rapidapi_host
            }
            params = {
                "query": f"{query} in {location_name}",
                "page": "1",
                "num_pages": "1",
                "date_posted": "all"
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                jobs_data = data.get("data", [])
                
                jobs = []
                for job in jobs_data[:max_results]:
                    jobs.append({
                        "title": job.get("job_title", ""),
                        "company": job.get("employer_name", "Unknown"),
                        "location": job.get("job_city", location_name),
                        "description": job.get("job_description", "")[:500],
                        "url": job.get("job_apply_link", job.get("job_google_link", "")),
                        "salary_min": job.get("job_min_salary"),
                        "salary_max": job.get("job_max_salary"),
                        "source": "JSearch (Indeed/LinkedIn/Glassdoor)"
                    })
                
                logger.info(f"Found {len(jobs)} jobs from JSearch")
                return jobs
            else:
                logger.error(f"JSearch API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching from JSearch: {e}")
            return []
    
    def search_jobs_themuse(self, skills: List[str], max_results: int = 10) -> List[Dict]:
        """
        Search jobs using The Muse API (FREE, no API key needed!)
        Docs: https://www.themuse.com/developers/api/v2
        Focus: Remote-friendly and company culture
        """
        try:
            url = "https://www.themuse.com/api/public/jobs"
            
            # Build query from skills
            query = " ".join(skills[:3])
            
            params = {
                "page": 0,
                "descending": "true",
                "api_key": "public"  # Public access
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                all_jobs = data.get("results", [])
                
                # Filter by skills
                matched_jobs = []
                skills_lower = [s.lower() for s in skills]
                
                for job in all_jobs:
                    job_title = job.get("name", "").lower()
                    job_categories = " ".join([cat.get("name", "") for cat in job.get("categories", [])]).lower()
                    job_levels = " ".join([level.get("name", "") for level in job.get("levels", [])]).lower()
                    
                    # Check for skill matches
                    match_count = sum(1 for skill in skills_lower 
                                     if skill in job_title or skill in job_categories or skill in job_levels)
                    
                    if match_count > 0:
                        company = job.get("company", {})
                        locations = job.get("locations", [])
                        location_str = locations[0].get("name", "Remote") if locations else "Remote"
                        
                        matched_jobs.append({
                            "title": job.get("name", ""),
                            "company": company.get("name", "Unknown"),
                            "location": location_str,
                            "description": job.get("contents", "")[:500],
                            "url": job.get("refs", {}).get("landing_page", ""),
                            "salary_min": None,
                            "salary_max": None,
                            "source": "The Muse"
                        })
                        
                        if len(matched_jobs) >= max_results:
                            break
                
                logger.info(f"Found {len(matched_jobs)} jobs from The Muse")
                return matched_jobs
            else:
                logger.error(f"The Muse API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching from The Muse: {e}")
            return []
    
    def search_jobs_jooble(self, skills: List[str], location: str = "in", max_results: int = 10) -> List[Dict]:
        """
        Search jobs using Jooble API (India support)
        Sign up: https://jooble.org/api/about
        Free tier: 1000 requests/day
        """
        try:
            # Check if API key is configured
            if self.jooble_api_key == "PASTE_YOUR_JOOBLE_KEY_HERE":
                logger.info("Jooble API key not configured, skipping")
                return []
            
            # Build search query
            keywords = " ".join(skills[:5])
            
            # Location mapping for Jooble
            location_map = {
                "in": "India",
                "us": "USA",
                "uk": "UK"
            }
            location_name = location_map.get(location, "India")
            
            url = f"https://jooble.org/api/{self.jooble_api_key}"
            payload = {
                "keywords": keywords,
                "location": location_name
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                jobs_data = data.get("jobs", [])
                
                jobs = []
                for job in jobs_data[:max_results]:
                    jobs.append({
                        "title": job.get("title", ""),
                        "company": job.get("company", "Unknown"),
                        "location": job.get("location", location_name),
                        "description": job.get("snippet", "")[:500],
                        "url": job.get("link", ""),
                        "salary_min": None,
                        "salary_max": None,
                        "source": "Jooble"
                    })
                
                logger.info(f"Found {len(jobs)} jobs from Jooble")
                return jobs
            else:
                logger.error(f"Jooble API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching from Jooble: {e}")
            return []
    
    def search_all_sources(self, skills: List[str], location: str = "in", max_results: int = 20) -> List[Dict]:
        """
        Search jobs from all available sources
        Returns combined list of jobs, prioritizing Indian jobs
        """
        all_jobs = []
        
        # Prioritize Indian jobs (always first)
        try:
            indian_jobs = self.search_indian_jobs(skills, max_results)
            all_jobs.extend(indian_jobs)
            logger.info(f"Added {len(indian_jobs)} Indian jobs")
        except Exception as e:
            logger.error(f"Error fetching Indian jobs: {e}")
        
        # Only fetch from external sources if we have very few Indian jobs
        # Priority: Quality > Quantity
        remaining = max_results - len(all_jobs)
        
        if remaining > 0 and len(all_jobs) < 3:
            # Try Adzuna India only if location is India
            if location == "in" or location == "india":
                try:
                    adzuna_jobs = self.search_jobs_adzuna(skills, "in", min(remaining, 3))
                    all_jobs.extend(adzuna_jobs)
                except Exception as e:
                    logger.error(f"Error fetching from Adzuna: {e}")
            
            # Try Remotive (remote jobs, can work from India)
            if len(all_jobs) < 3:
                try:
                    remotive_jobs = self.search_jobs_remotive(skills, min(remaining, 2))
                    all_jobs.extend(remotive_jobs)
                except Exception as e:
                    logger.error(f"Error fetching from Remotive: {e}")
            
            # Try Arbeitnow
            if len(all_jobs) < 3:
                try:
                    arbeitnow_jobs = self.search_jobs_github(skills, location, min(remaining, 2))
                    all_jobs.extend(arbeitnow_jobs)
                except Exception as e:
                    logger.error(f"Error fetching from Arbeitnow: {e}")
            
            # Try JSearch (RapidAPI) - Multi-source aggregator
            if len(all_jobs) < 5:
                try:
                    jsearch_jobs = self.search_jobs_jsearch(skills, location, min(remaining, 3))
                    all_jobs.extend(jsearch_jobs)
                except Exception as e:
                    logger.error(f"Error fetching from JSearch: {e}")
            
            # Try The Muse API (no key needed)
            if len(all_jobs) < 5:
                try:
                    muse_jobs = self.search_jobs_themuse(skills, min(remaining, 3))
                    all_jobs.extend(muse_jobs)
                except Exception as e:
                    logger.error(f"Error fetching from The Muse: {e}")
            
            # Try Jooble (India support)
            if len(all_jobs) < 5 and location in ["in", "india"]:
                try:
                    jooble_jobs = self.search_jobs_jooble(skills, location, min(remaining, 3))
                    all_jobs.extend(jooble_jobs)
                except Exception as e:
                    logger.error(f"Error fetching from Jooble: {e}")
        
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


def fetch_jobs_for_skills(skills: List[str], location: str = "in", max_results: int = 20) -> List[Dict]:
    """
    Fetch jobs matching the given skills (defaults to India)
    
    Args:
        skills: List of skills to search for
        location: Location code (in=India, us=USA, uk=UK, etc.)
        max_results: Maximum number of jobs to return
    
    Returns:
        List of job dictionaries with Indian jobs prioritized
    """
    return job_search_api.search_all_sources(skills, location, max_results)
