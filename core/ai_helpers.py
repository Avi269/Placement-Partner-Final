"""
============================================================================
AI HELPERS - With Fallback to Regex Patterns
============================================================================
Tries AI first, falls back to regex patterns when quota exceeded
"""

import json
import logging
import re
import google.generativeai as genai
from typing import Dict, List, Optional
from django.core.exceptions import ValidationError
from django.conf import settings
from time import sleep

logger = logging.getLogger(__name__)

# ============================================================================
# FALLBACK PATTERNS (When AI quota exceeded)
# ============================================================================

EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
PHONE_PATTERNS = [
    r'\+91[\s-]?\d{10}',
    r'\d{10}',
    r'\+\d{1,3}[\s-]?\d{9,12}'
]

SKILL_PATTERNS = [
    r'\b(python|java|javascript|typescript|c\+\+|c#|ruby|php|swift|kotlin|scala|rust|go|perl|r|matlab)\b',
    r'\b(react|angular|vue|node\.?js|django|flask|spring|express|laravel|rails|asp\.net|fastapi)\b',
    r'\b(sql|mysql|postgresql|mongodb|oracle|redis|cassandra|dynamodb|sqlite|mariadb)\b',
    r'\b(aws|azure|gcp|docker|kubernetes|jenkins|terraform|ansible|ci/cd|devops)\b',
    r'\b(machine learning|deep learning|tensorflow|pytorch|scikit-learn|pandas|numpy|keras|opencv)\b',
    r'\b(git|github|gitlab|jira|confluence|slack|tableau|power bi|excel|linux|unix)\b'
]

# ============================================================================
# RETRY HELPER WITH QUOTA DETECTION
# ============================================================================

def generate_with_retry(prompt: str, max_retries: int = 2, temperature: float = 0.7, max_tokens: int = 1024):  # ✅ Changed from 512 to 1024
    """Helper function with retry logic and quota detection"""
    for attempt in range(max_retries):
        try:
            model = genai.GenerativeModel(settings.GEMINI_MODEL)
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,  # This controls the length
            )
            response = model.generate_content(prompt, generation_config=generation_config)
            
            if not response or not hasattr(response, 'text') or not response.text:
                if attempt < max_retries - 1:
                    sleep(1)
                    continue
                raise ValueError("Empty response from API")
            
            return response
            
        except Exception as e:
            error_str = str(e)
            
            # Check if it's a quota error
            if '429' in error_str or 'quota' in error_str.lower():
                logger.warning(f"⚠️ API quota exceeded - falling back to regex patterns")
                raise QuotaExceededException("API quota exceeded")
            
            if attempt == max_retries - 1:
                raise ValidationError(f"AI generation failed: {str(e)}")
            
            sleep(1)


class QuotaExceededException(Exception):
    """Custom exception for quota errors"""
    pass


# ============================================================================
# RESUME DATA EXTRACTION - WITH FALLBACK
# ============================================================================

def extract_resume_data_with_ai(text: str) -> Dict:
    """
    Try AI extraction first, fall back to regex if quota exceeded
    """
    try:
        # Try AI parsing
        return _ai_extract_resume(text)
    except QuotaExceededException:
        logger.warning("🔄 Using fallback regex extraction due to quota limits")
        return _fallback_extract_resume(text)
    except Exception as e:
        logger.error(f"AI resume parsing failed: {e}")
        return _fallback_extract_resume(text)


def _ai_extract_resume(text: str) -> Dict:
    """AI-powered extraction (throws QuotaExceededException if quota exceeded)"""
    prompt = f"""
Extract resume data as JSON. Return:
{{
  "name": "Full Name",
  "email": "email@domain.com",
  "phone": "+1234567890",
  "skills": ["Python", "Django"],
  "education": ["B.Tech CS, XYZ University, 2020-2024"],
  "experience": ["Software Engineer at Company, 2023-Present"]
}}

Resume (first 2000 chars):
{text[:2000]}
"""
    
    response = generate_with_retry(prompt, temperature=0.0, max_tokens=1000, max_retries=2)
    raw = response.text.strip()
    
    # Clean JSON
    raw = re.sub(r'```json\n?', '', raw)
    raw = re.sub(r'```\n?', '', raw)
    
    data = json.loads(raw)
    data["parsed_text"] = text[:2000]
    return data


def _fallback_extract_resume(text: str) -> Dict:
    """Regex-based fallback extraction"""
    logger.info("📝 Using regex-based extraction")
    
    # Extract email
    email_match = re.search(EMAIL_PATTERN, text, re.IGNORECASE)
    email = email_match.group(0) if email_match else ""
    
    # Extract phone
    phone = ""
    for pattern in PHONE_PATTERNS:
        phone_match = re.search(pattern, text)
        if phone_match:
            phone = phone_match.group(0)
            break
    
    # Extract skills
    skills = set()
    for pattern in SKILL_PATTERNS:
        matches = re.findall(pattern, text.lower(), re.IGNORECASE)
        skills.update(matches)
    
    # Extract name (first line that looks like a name)
    name_match = re.search(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})$', text, re.MULTILINE)
    name = name_match.group(1) if name_match else ""
    
    # Extract education
    education = re.findall(
        r'(B\.?Tech|M\.?Tech|Bachelor|Master|MBA|MCA|BCA|BSc|MSc).*?(?:University|College|Institute)',
        text,
        re.IGNORECASE
    )
    
    # Extract experience
    experience = re.findall(
        r'((?:Software|Senior|Junior|Lead)?\s*(?:Engineer|Developer|Analyst|Manager)).*?(?:at|@)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        text
    )
    experience_list = [f"{title} at {company}" for title, company in experience[:3]]
    
    return {
        "name": name,
        "email": email,
        "phone": phone,
        "skills": list(skills)[:20],
        "education": education[:3],
        "experience": experience_list,
        "parsed_text": text[:2000]
    }


# ============================================================================
# SKILL EXTRACTION - WITH FALLBACK
# ============================================================================

def extract_skills_with_ai(text: str, context: str = "resume") -> List[str]:
    """Extract skills with fallback to regex"""
    try:
        # Try AI
        prompt = f"""
Extract ONLY technical skills from this {context}.
Return JSON array: ["Python", "Django", "React"]

Text:
{text[:1500]}
"""
        response = generate_with_retry(prompt, temperature=0.0, max_tokens=200, max_retries=2)
        raw = response.text.strip()
        raw = re.sub(r'```json\n?', '', raw)
        raw = re.sub(r'```\n?', '', raw)
        
        skills = json.loads(raw)
        return skills if isinstance(skills, list) else []
        
    except (QuotaExceededException, Exception) as e:
        logger.warning(f"🔄 Using regex for skill extraction: {e}")
        # Fallback to regex
        skills = set()
        for pattern in SKILL_PATTERNS:
            matches = re.findall(pattern, text.lower(), re.IGNORECASE)
            skills.update(matches)
        return list(skills)[:30]


# ============================================================================
# LEARNING RESOURCES - STATIC FALLBACK
# ============================================================================

def get_learning_resources_with_ai(skills: List[str]) -> List[Dict]:
    """Get resources with static fallback"""
    try:
        # Try AI
        skills_str = ", ".join(skills[:5])
        prompt = f"""
For each skill, provide 2 learning resources as JSON:
[{{"skill": "Python", "resources": [{{"title": "...", "url": "...", "type": "tutorial", "description": "...", "duration": "10 hours"}}]}}]

Skills: {skills_str}
"""
        response = generate_with_retry(prompt, temperature=0.3, max_tokens=1500, max_retries=1)
        raw = response.text.strip()
        raw = re.sub(r'```json\n?', '', raw)
        raw = re.sub(r'```\n?', '', raw)
        
        return json.loads(raw)
        
    except (QuotaExceededException, Exception) as e:
        logger.warning(f"🔄 Using static resource links: {e}")
        # Fallback to static resources
        return _static_learning_resources(skills)


def _static_learning_resources(skills: List[str]) -> List[Dict]:
    """Static fallback resources"""
    resources = []
    for skill in skills[:10]:
        resources.append({
            "skill": skill,
            "resources": [
                {
                    "title": f"{skill.title()} Tutorial on YouTube",
                    "url": f"https://www.youtube.com/results?search_query={skill}+tutorial+2024",
                    "type": "video",
                    "description": f"Video tutorials for {skill}",
                    "duration": "Varies"
                },
                {
                    "title": f"{skill.title()} on Udemy",
                    "url": f"https://www.udemy.com/courses/search/?q={skill}",
                    "type": "course",
                    "description": f"Professional courses on {skill}",
                    "duration": "10-30 hours"
                },
                {
                    "title": f"{skill.title()} Documentation",
                    "url": f"https://www.google.com/search?q={skill}+official+documentation",
                    "type": "docs",
                    "description": f"Official {skill} documentation",
                    "duration": "Self-paced"
                }
            ]
        })
    return resources


# ============================================================================
# JOB FIT ANALYSIS - WITH BASIC FALLBACK
# ============================================================================

def analyze_job_fit_with_ai(resume_text: str, job_description: str) -> Dict:
    """Job fit analysis with basic scoring fallback"""
    try:
        # Try AI analysis
        prompt = f"""
Analyze job fit. Return JSON:
{{"fit_score": 0-100, "matching_skills": [], "missing_skills": [], "strengths": [], "gaps": []}}

Resume: {resume_text[:800]}
Job: {job_description[:800]}
"""
        response = generate_with_retry(prompt, temperature=0.2, max_tokens=800, max_retries=1)
        raw = response.text.strip()
        raw = re.sub(r'```json\n?', '', raw)
        raw = re.sub(r'```\n?', '', raw)
        
        return json.loads(raw)
        
    except (QuotaExceededException, Exception) as e:
        logger.warning(f"🔄 Using basic fit calculation: {e}")
        return _basic_job_fit(resume_text, job_description)


def _basic_job_fit(resume_text: str, jd_text: str) -> Dict:
    """Basic keyword-based job fit"""
    # Extract skills from both
    resume_skills = set()
    jd_skills = set()
    
    for pattern in SKILL_PATTERNS:
        resume_skills.update(re.findall(pattern, resume_text.lower()))
        jd_skills.update(re.findall(pattern, jd_text.lower()))
    
    matching = resume_skills.intersection(jd_skills)
    missing = jd_skills - resume_skills
    
    fit_score = (len(matching) / len(jd_skills) * 100) if jd_skills else 0
    
    return {
        "fit_score": round(fit_score, 1),
        "matching_skills": list(matching),
        "missing_skills": list(missing),
        "strengths": [f"You have {len(matching)} matching skills"],
        "gaps": [f"Consider learning: {', '.join(list(missing)[:3])}"] if missing else [],
        "interview_readiness": "high" if fit_score > 70 else "medium" if fit_score > 40 else "low"
    }


# Keep other AI functions (cover letter, offer analysis) as they are less frequent
def get_job_recommendations_with_ai(skills: List[str], experience_level: str = "entry") -> List[Dict]:
    """Simplified - returns empty if quota exceeded"""
    try:
        # Try AI (reduced token usage)
        skills_str = ", ".join(skills[:8])
        prompt = f"Suggest 3 jobs for: {skills_str}. Return JSON: [{{'title':'...', 'match_score':85}}]"
        
        response = generate_with_retry(prompt, temperature=0.4, max_tokens=500, max_retries=1)
        raw = re.sub(r'```json\n?', '', response.text.strip())
        raw = re.sub(r'```\n?', '', raw)
        return json.loads(raw)
    except:
        return []  # Return empty, let external job API handle it


def optimize_resume_with_ai(resume_text: str, job_description: str = "") -> Dict:
    """Simplified optimization"""
    try:
        prompt = f"ATS score for resume. Return JSON: {{'ats_score': 75, 'action_items': ['...']}}\n\nResume: {resume_text[:1000]}"
        response = generate_with_retry(prompt, temperature=0.3, max_tokens=400, max_retries=1)
        raw = re.sub(r'```json\n?', '', response.text.strip())
        return json.loads(re.sub(r'```\n?', '', raw))
    except:
        return {"ats_score": 70, "action_items": ["Review formatting", "Add more keywords"]}


# Keep cover letter and offer analysis as-is (users trigger these explicitly)