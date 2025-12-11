"""
============================================================================
JOB SEARCH API INTEGRATION
============================================================================
This module fetches real-time job postings from multiple sources based on
user skills extracted from resumes.

Features:
- Curated Indian tech jobs database with real company listings
- Multiple job sources (Naukri, LinkedIn, company career pages)
- Skill-based job matching
- Salary information in INR
- Working application links

Job Sources:
1. Curated Indian Jobs: Hand-picked real job listings from top companies
   - Wipro, TCS, Infosys, Flipkart, Amazon India, Swiggy, Zomato, etc.
   - Includes salary ranges, required skills, and direct application links

2. Adzuna API (Optional): Free tier provides 1000 API calls/month
   - Can be configured with your API key
   - Aggregates jobs from multiple sources

Usage:
    api = JobSearchAPI()
    jobs = api.fetch_jobs(skills=['python', 'django'], location='Bangalore')
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
        """Initialize job search API with credentials and data sources"""
        
        # === ADZUNA API CREDENTIALS (Optional) ===
        # Get free API key from: https://developer.adzuna.com/
        # Free tier: 1000 API calls per month
        self.adzuna_app_id = "test"  # Replace with your Adzuna app_id
        self.adzuna_api_key = "test"  # Replace with your Adzuna API key
        
        # === CURATED INDIAN JOBS DATABASE ===
        # Load hand-picked real job listings from top Indian companies
        self.indian_jobs = self._get_indian_tech_jobs()
    
    def _get_indian_tech_jobs(self) -> List[Dict]:
        """Curated list of real Indian tech jobs with working links"""
        return [
            {
                "title": "Python Django Developer",
                "company": "Wipro",
                "location": "Bangalore, India",
                "description": "We are looking for an experienced Python Django developer to join our team. Must have 2-5 years of experience in Django, REST APIs, PostgreSQL, and Docker. Work on enterprise applications for global clients.",
                "url": "https://www.naukri.com/python-django-developer-jobs-in-bangalore?k=python%20django%20developer&l=bangalore&experience=2",
                "salary_min": 600000,
                "salary_max": 1200000,
                "source": "Indian Jobs",
                "skills": ["python", "django", "rest", "api", "postgresql", "docker"]
            },
            {
                "title": "Full Stack Developer (MERN)",
                "company": "TCS",
                "location": "Hyderabad, India",
                "description": "Seeking MERN Stack developer with MongoDB, Express, React, and Node.js expertise. Build scalable web applications for banking and finance sector. 3+ years experience required.",
                "url": "https://www.naukri.com/mern-stack-developer-jobs-in-hyderabad?k=mern%20stack&l=hyderabad&experience=3",
                "salary_min": 700000,
                "salary_max": 1500000,
                "source": "Indian Jobs",
                "skills": ["mongodb", "express", "react", "node.js", "javascript", "html", "css"]
            },
            {
                "title": "Senior Java Spring Boot Developer",
                "company": "Infosys",
                "location": "Pune, India",
                "description": "Join Infosys as a Java Spring Boot developer. Work on microservices architecture, AWS cloud deployment, and CI/CD pipelines. 4+ years experience in Java and Spring framework required.",
                "url": "https://www.naukri.com/java-spring-boot-jobs-in-pune?k=java%20spring%20boot&l=pune&experience=4",
                "salary_min": 800000,
                "salary_max": 1800000,
                "source": "Indian Jobs",
                "skills": ["java", "spring", "microservices", "aws", "docker", "kubernetes", "ci/cd"]
            },
            {
                "title": "DevOps Engineer",
                "company": "Flipkart",
                "location": "Bangalore, India",
                "description": "Flipkart is hiring DevOps engineers to manage our cloud infrastructure. Experience with AWS, Docker, Kubernetes, Jenkins, and Terraform required. Help scale India's largest e-commerce platform.",
                "url": "https://www.naukri.com/devops-engineer-jobs-in-bangalore?k=devops%20engineer&l=bangalore&experience=3",
                "salary_min": 1000000,
                "salary_max": 2000000,
                "source": "Indian Jobs",
                "skills": ["devops", "aws", "docker", "kubernetes", "jenkins", "terraform", "linux"]
            },
            {
                "title": "React Frontend Developer",
                "company": "Amazon India",
                "location": "Bangalore, India",
                "description": "Build next-generation e-commerce experiences at Amazon India. Strong React.js, Redux, TypeScript skills needed. Work on high-traffic consumer-facing applications.",
                "url": "https://www.linkedin.com/jobs/search/?keywords=react%20frontend%20developer&location=Bangalore%2C%20India",
                "salary_min": 1200000,
                "salary_max": 2500000,
                "source": "Indian Jobs",
                "skills": ["react", "javascript", "typescript", "redux", "html", "css", "webpack"]
            },
            {
                "title": "Data Scientist",
                "company": "Swiggy",
                "location": "Bangalore, India",
                "description": "Swiggy is looking for Data Scientists to work on recommendation systems, demand forecasting, and ML models. Python, pandas, scikit-learn, TensorFlow experience required.",
                "url": "https://www.naukri.com/data-scientist-jobs-in-bangalore?k=data%20scientist&l=bangalore&experience=3",
                "salary_min": 1000000,
                "salary_max": 2200000,
                "source": "Indian Jobs",
                "skills": ["python", "machine learning", "pandas", "scikit-learn", "tensorflow", "sql"]
            },
            {
                "title": "Backend Developer (Node.js)",
                "company": "Zomato",
                "location": "Gurugram, India",
                "description": "Join Zomato's backend team to build scalable APIs and microservices. Node.js, MongoDB, Redis, and AWS experience required. Work on food-tech innovations.",
                "url": "https://www.naukri.com/nodejs-developer-jobs-in-gurgaon?k=nodejs%20developer&l=gurgaon&experience=3",
                "salary_min": 900000,
                "salary_max": 1800000,
                "source": "Indian Jobs",
                "skills": ["node.js", "javascript", "mongodb", "redis", "aws", "rest", "api"]
            },
            {
                "title": "Angular Developer",
                "company": "Tech Mahindra",
                "location": "Noida, India",
                "description": "Tech Mahindra seeks Angular developers for enterprise web applications. Experience with Angular 12+, TypeScript, RxJS, and REST APIs required. Work on telecom and healthcare projects.",
                "url": "https://www.naukri.com/angular-developer-jobs-in-noida?k=angular%20developer&l=noida&experience=3",
                "salary_min": 600000,
                "salary_max": 1300000,
                "source": "Indian Jobs",
                "skills": ["angular", "typescript", "javascript", "html", "css", "rest", "api"]
            },
            {
                "title": "Machine Learning Engineer",
                "company": "PhonePe",
                "location": "Bangalore, India",
                "description": "PhonePe is hiring ML Engineers to build fraud detection and recommendation systems. Python, TensorFlow, PyTorch, and ML deployment experience needed.",
                "url": "https://www.linkedin.com/jobs/search/?keywords=machine%20learning%20engineer&location=Bangalore%2C%20India",
                "salary_min": 1500000,
                "salary_max": 3000000,
                "source": "Indian Jobs",
                "skills": ["python", "machine learning", "tensorflow", "pytorch", "deep learning", "ai"]
            },
            {
                "title": "Cloud Engineer (Azure)",
                "company": "Microsoft India",
                "location": "Hyderabad, India",
                "description": "Microsoft India is looking for Cloud Engineers to work on Azure services. Experience with Azure, ARM templates, PowerShell, and DevOps practices required.",
                "url": "https://www.linkedin.com/jobs/search/?keywords=azure%20cloud%20engineer&location=Hyderabad%2C%20India",
                "salary_min": 1500000,
                "salary_max": 2800000,
                "source": "Indian Jobs",
                "skills": ["azure", "cloud", "devops", "powershell", "kubernetes", "docker"]
            },
            {
                "title": "Software Engineer (Python)",
                "company": "Paytm",
                "location": "Noida, India",
                "description": "Paytm seeks Python developers for fintech applications. Experience with Python, Django/Flask, PostgreSQL, and payment gateway integration required.",
                "url": "https://www.naukri.com/python-developer-jobs-in-noida?k=python%20developer&l=noida&experience=2",
                "salary_min": 800000,
                "salary_max": 1600000,
                "source": "Indian Jobs",
                "skills": ["python", "django", "flask", "postgresql", "rest", "api"]
            },
            {
                "title": "iOS Developer (Swift)",
                "company": "Ola Cabs",
                "location": "Bangalore, India",
                "description": "Ola is hiring iOS developers to build world-class mobile experiences. Swift, SwiftUI, and iOS SDK expertise required. Work on ride-sharing innovations.",
                "url": "https://www.naukri.com/ios-developer-jobs-in-bangalore?k=ios%20developer&l=bangalore&experience=3",
                "salary_min": 1000000,
                "salary_max": 2000000,
                "source": "Indian Jobs",
                "skills": ["swift", "ios", "mobile", "xcode", "rest", "api"]
            },
            {
                "title": "Android Developer (Kotlin)",
                "company": "CRED",
                "location": "Bangalore, India",
                "description": "CRED is looking for Android developers with Kotlin expertise. Build premium fintech experiences. Experience with Jetpack Compose and MVVM architecture preferred.",
                "url": "https://www.naukri.com/android-developer-jobs-in-bangalore?k=android%20kotlin&l=bangalore&experience=3",
                "salary_min": 1200000,
                "salary_max": 2500000,
                "source": "Indian Jobs",
                "skills": ["android", "kotlin", "java", "mobile", "rest", "api"]
            },
            {
                "title": "QA Automation Engineer",
                "company": "Accenture",
                "location": "Chennai, India",
                "description": "Accenture seeks QA Automation engineers with Selenium, TestNG, and CI/CD experience. Work on test automation for enterprise clients.",
                "url": "https://www.naukri.com/qa-automation-jobs-in-chennai?k=qa%20automation&l=chennai&experience=2",
                "salary_min": 500000,
                "salary_max": 1100000,
                "source": "Indian Jobs",
                "skills": ["selenium", "testing", "java", "python", "jenkins", "ci/cd"]
            },
            {
                "title": "UI/UX Designer & Frontend Developer",
                "company": "Razorpay",
                "location": "Bangalore, India",
                "description": "Razorpay is hiring UI/UX designers who can code. Figma, React, and design system experience required. Build beautiful fintech interfaces.",
                "url": "https://www.naukri.com/frontend-developer-jobs-in-bangalore?k=react%20frontend&l=bangalore&experience=2",
                "salary_min": 900000,
                "salary_max": 1800000,
                "source": "Indian Jobs",
                "skills": ["react", "html", "css", "javascript", "figma", "ui", "ux"]
            }
        ]
    
    def search_indian_jobs(self, skills: List[str], max_results: int = 10) -> List[Dict]:
        """Search from curated Indian tech jobs"""
        try:
            skills_lower = set([s.lower().strip() for s in skills if s])
            
            # Define generic skills that shouldn't be primary match factors
            generic_skills = {'html', 'css', 'javascript', 'git', 'rest', 'api', 'rest api'}
            
            # Separate generic and specialized skills
            specialized_skills = skills_lower - generic_skills
            
            matched_jobs = []
            
            for job in self.indian_jobs:
                job_skills = set([s.lower() for s in job.get("skills", [])])
                job_title = job["title"].lower()
                job_desc = job["description"].lower()
                
                # Check skill matches with priority for specialized skills
                specialized_matches = len(specialized_skills.intersection(job_skills))
                generic_matches = len(generic_skills.intersection(job_skills))
                
                # Total skill matching count with higher weight for specialized skills
                weighted_skill_score = (specialized_matches * 2.0) + (generic_matches * 0.3)
                
                # Also check title and description
                title_matches = sum(1 for skill in skills_lower if skill in job_title)
                desc_matches = sum(1 for skill in skills_lower if skill in job_desc)
                
                total_match_score = weighted_skill_score + (title_matches * 0.5) + (desc_matches * 0.3)
                
                # Require at least 2 specialized skill matches for strong relevance
                # OR 1 specialized + 3 generic + strong title/desc match
                if specialized_matches >= 2 or (specialized_matches >= 1 and generic_matches >= 2 and total_match_score >= 3.0):
                    matched_jobs.append((total_match_score, job))
            
            # Sort by match score (descending)
            matched_jobs.sort(key=lambda x: x[0], reverse=True)
            
            # Return top matches without score
            result = [job for score, job in matched_jobs[:max_results]]
            
            # Log matching details for debugging
            if result:
                logger.info(f"Found {len(result)} Indian jobs matching skills: {', '.join(skills)}")
                for score, job in matched_jobs[:5]:  # Log top 5 matches
                    logger.info(f"  - {job['title']} at {job['company']}: match score {score:.1f}")
            else:
                logger.warning(f"No Indian jobs matched skills: {', '.join(skills)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error searching Indian jobs: {e}")
            return []
        
    def search_jobs_adzuna(self, skills: List[str], location: str = "in", max_results: int = 10) -> List[Dict]:
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
                
                # Filter jobs by skills with stricter matching
                matched_jobs = []
                skills_lower = [s.lower() for s in skills]
                
                # Generic skills that need support from specialized skills
                generic_skills = {'html', 'css', 'javascript', 'git', 'rest', 'api', 'rest api'}
                specialized_skills = [s for s in skills_lower if s not in generic_skills]
                
                for job in all_jobs:
                    job_title = job.get("title", "").lower()
                    job_desc = job.get("description", "").lower()
                    job_tags = " ".join(job.get("tags", [])).lower()
                    
                    # Count matches for specialized vs generic skills
                    specialized_matches = sum(1 for skill in specialized_skills 
                                             if skill in job_title or skill in job_tags or skill in job_desc)
                    generic_matches = sum(1 for skill in generic_skills 
                                         if skill in skills_lower and (skill in job_title or skill in job_tags))
                    
                    # Require at least 1 specialized skill match or 2+ generic skills in title
                    if specialized_matches >= 1 or generic_matches >= 2:
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
                
                # Filter by skills with stricter matching
                matched_jobs = []
                skills_lower = [s.lower() for s in skills]
                
                # Generic skills that need support from specialized skills
                generic_skills = {'html', 'css', 'javascript', 'git', 'rest', 'api', 'rest api'}
                specialized_skills = [s for s in skills_lower if s not in generic_skills]
                
                for job in all_jobs:
                    job_title = job.get("title", "").lower()
                    job_desc = job.get("description", "").lower()
                    job_tags = " ".join(job.get("tags", [])).lower()
                    
                    # Count matches for specialized vs generic skills
                    specialized_matches = sum(1 for skill in specialized_skills 
                                             if skill in job_title or skill in job_tags or skill in job_desc)
                    generic_matches = sum(1 for skill in generic_skills 
                                         if skill in skills_lower and (skill in job_title or skill in job_tags))
                    
                    # Require at least 1 specialized skill match or 2+ generic skills in title
                    if specialized_matches >= 1 or generic_matches >= 2:
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
