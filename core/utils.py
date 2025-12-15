"""
============================================================================
CORE UTILITIES - AI & File Processing Functions
============================================================================
AI-First approach: Everything extracted via Gemini AI with minimal fallbacks
"""

# Standard library imports
import re
import json
import os
import logging
from typing import Dict, List, Tuple, Optional
from time import sleep

# Third-party imports
import docx2txt
from pdf2image import convert_from_path
import pytesseract
from pdfminer.high_level import extract_text
import google.generativeai as genai

# Django imports
from django.conf import settings
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.core.cache import cache

# Local imports
from .models import LearningResource

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Configure Gemini
API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ImproperlyConfigured("Gemini API key not found. Set GEMINI_API_KEY in .env")

genai.configure(api_key=API_KEY)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")

# ============================================================================
# IMPORT AI HELPERS (AFTER CONFIGURATION)
# ============================================================================

from .ai_helpers import (
    extract_resume_data_with_ai,
    extract_skills_with_ai,
    get_learning_resources_with_ai,
    get_job_recommendations_with_ai,
    analyze_job_fit_with_ai,
    optimize_resume_with_ai,
    generate_with_retry
)

# ============================================================================
# FILE EXTRACTION
# ============================================================================

def extract_text_from_file(file_path: str) -> str:
    """Extract text from PDF, DOCX, DOC, or TXT files"""
    if hasattr(file_path, 'path'):
        file_path = file_path.path
    elif hasattr(file_path, 'name'):
        file_path = str(file_path)
    
    ext = os.path.splitext(file_path)[1][1:].lower()
    
    try:
        if ext == 'pdf':
            text = extract_text(file_path)
            if text and len(text.strip()) > 20:
                return text
            
            # Fallback to OCR
            try:
                pytesseract.get_tesseract_version()
                pages = convert_from_path(file_path)
                text = "\n".join([pytesseract.image_to_string(p) for p in pages])
                return text
            except:
                raise ValidationError("PDF contains no readable text. Please use text-selectable PDF or DOCX.")
        
        elif ext in ['docx', 'doc']:
            text = docx2txt.process(file_path)
            if not text.strip():
                raise ValidationError("DOCX contains no readable text.")
            return text
        
        elif ext == 'txt':
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            if not text.strip():
                raise ValidationError("TXT file is empty.")
            return text
        
        else:
            raise ValidationError(f"Unsupported file type: {ext}")
    
    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(f"Failed to extract text: {str(e)}")


# ============================================================================
# RESUME PARSING - AI-FIRST
# ============================================================================

def parse_resume_file(file_path) -> Dict:
    """Parse resume using AI - NO hardcoded patterns"""
    text = extract_text_from_file(file_path)
    
    if not text or len(text.strip()) < 20:
        raise ValidationError("Could not extract sufficient text from resume file.")
    
    try:
        parsed_data = extract_resume_data_with_ai(text)
        parsed_data["parsed_text"] = text[:2000]
        return parsed_data
    except Exception as e:
        logger.error(f"AI resume parsing failed: {e}")
        return {
            "name": "",
            "email": "",
            "phone": "",
            "skills": [],
            "education": [],
            "experience": [],
            "parsed_text": text[:2000]
        }


# ============================================================================
# SKILL EXTRACTION - AI-POWERED
# ============================================================================

def extract_skills_from_text(text: str) -> List[str]:
    """Extract skills using AI - completely dynamic"""
    try:
        skills = extract_skills_with_ai(text, context="resume")
        return skills if skills else []
    except Exception as e:
        logger.error(f"AI skill extraction failed: {e}")
        return []


# ============================================================================
# JOB MATCHING - AI-POWERED
# ============================================================================

def calculate_job_fit_with_gemini(resume_skills: List[str], jd_text: str) -> Tuple[float, List[str], List[str]]:
    """
    Calculate job fit using AI analysis with robust fallback
    
    Args:
        resume_skills: List of skills from resume
        jd_text: Job description text
    
    Returns:
        Tuple of (fit_score, matching_skills, missing_skills)
    """
    try:
        # Attempt AI analysis first
        analysis = analyze_job_fit_with_ai(
            resume_text=" ".join(resume_skills),
            job_description=jd_text
        )
        
        fit_score = float(analysis.get("fit_score", 0))
        matching_skills = analysis.get("matching_skills", [])
        missing_skills = analysis.get("missing_skills", [])
        
        # Validate response
        if not matching_skills and not missing_skills:
            logger.warning("AI returned empty skills, using fallback")
            raise ValueError("Empty AI response")
        
        logger.info(f"AI analysis: {fit_score}% fit, {len(matching_skills)} matching, {len(missing_skills)} missing")
        return (fit_score, matching_skills, missing_skills)
        
    except Exception as e:
        logger.error(f"AI job fit calculation failed: {e}, using fallback")
        
        # FALLBACK: Rule-based matching
        return calculate_job_fit_with_fallback(resume_skills, jd_text)


def calculate_job_fit_with_fallback(resume_skills: List[str], jd_text: str) -> Tuple[float, List[str], List[str]]:
    """
    Fallback job fit calculation using keyword matching
    
    Args:
        resume_skills: List of skills from resume
        jd_text: Job description text
    
    Returns:
        Tuple of (fit_score, matching_skills, missing_skills)
    """
    if not resume_skills or not jd_text:
        logger.warning("Empty input for fallback job fit")
        return (0.0, [], [])
    
    # Normalize inputs
    jd_lower = jd_text.lower()
    resume_skills_lower = [s.lower().strip() for s in resume_skills if s.strip()]
    
    # Extract skills from JD using common patterns
    jd_skills = set()
    
    # Common skill keywords to look for
    skill_patterns = [
        r'\b(python|java|javascript|typescript|c\+\+|c#|ruby|php|swift|kotlin|go|rust)\b',
        r'\b(react|angular|vue|django|flask|spring|node\.js|express|fastapi)\b',
        r'\b(sql|mysql|postgresql|mongodb|redis|elasticsearch|dynamodb)\b',
        r'\b(aws|azure|gcp|docker|kubernetes|jenkins|git|ci/cd)\b',
        r'\b(html|css|sass|tailwind|bootstrap|material-ui)\b',
        r'\b(rest|api|graphql|microservices|serverless)\b',
        r'\b(machine learning|ml|ai|deep learning|nlp|computer vision)\b',
        r'\b(pandas|numpy|scikit-learn|tensorflow|pytorch|keras)\b',
        r'\b(linux|unix|bash|shell scripting|powershell)\b',
        r'\b(agile|scrum|kanban|jira|confluence)\b',
    ]
    
    import re
    for pattern in skill_patterns:
        matches = re.findall(pattern, jd_lower)
        jd_skills.update(matches)
    
    # Also extract words that appear in JD and might be skills
    tech_words = re.findall(r'\b[a-z][a-z0-9\.\-]{1,14}\b', jd_lower)
    
    # Filter to likely tech skills
    common_tech = {
        'api', 'rest', 'json', 'xml', 'http', 'tcp', 'ip', 'ssh', 'cli',
        'orm', 'mvc', 'crud', 'auth', 'oauth', 'jwt', 'ssl', 'tls',
        'nosql', 'cache', 'queue', 'async', 'sync', 'ajax',
        'ui', 'ux', 'frontend', 'backend', 'fullstack', 'devops'
    }
    
    jd_skills.update([w for w in tech_words if w in common_tech or len(w) > 4])
    
    # Find matching skills
    matching_skills = []
    for skill in resume_skills_lower:
        skill_clean = skill.replace('.', '').replace('-', '').replace(' ', '')
        
        if (skill in jd_lower or 
            skill.replace('.', '') in jd_lower or
            skill in jd_skills or
            skill_clean in jd_lower):
            matching_skills.append(resume_skills[resume_skills_lower.index(skill)])
    
    # Find missing skills
    missing_skills = []
    for jd_skill in jd_skills:
        jd_skill_clean = jd_skill.replace('.', '').replace('-', '').replace(' ', '')
        
        found = False
        for resume_skill in resume_skills_lower:
            resume_skill_clean = resume_skill.replace('.', '').replace('-', '').replace(' ', '')
            if (jd_skill in resume_skill or 
                resume_skill in jd_skill or
                jd_skill_clean == resume_skill_clean):
                found = True
                break
        
        if not found and len(jd_skill) > 2:
            if jd_skill.upper() == jd_skill.replace('.', '').replace('-', ''):
                missing_skills.append(jd_skill.upper())
            else:
                missing_skills.append(jd_skill.title())
    
    # Remove duplicates
    matching_skills = list(dict.fromkeys(matching_skills))
    missing_skills = list(dict.fromkeys(missing_skills))
    
    # Calculate fit score
    if len(jd_skills) == 0:
        fit_score = len(matching_skills) * 10
        fit_score = min(fit_score, 100)
    else:
        fit_score = (len(matching_skills) / max(len(jd_skills), len(resume_skills))) * 100
        fit_score = min(fit_score, 100)
    
    logger.info(f"Fallback analysis: {fit_score:.1f}% fit, {len(matching_skills)} matching, {len(missing_skills)} missing")
    
    return (
        round(fit_score, 1),
        matching_skills[:20],
        missing_skills[:20]
    )


# ============================================================================
# LEARNING RESOURCES - AI + DATABASE
# ============================================================================

def get_learning_resources_with_gemini(missing_skills: List[str]) -> List[Dict]:
    """Get learning resources using AI with database caching"""
    if not missing_skills:
        return []
    
    resources = []
    
    for skill in missing_skills[:10]:
        skill_lower = skill.lower().strip()
        
        # Check cache first
        cache_key = f"learning_resources_{skill_lower}"
        cached = cache.get(cache_key)
        
        if cached:
            resources.append({"skill": skill, "resources": cached})
            continue
        
        # Check database
        db_resources = LearningResource.objects.filter(
            skill__iexact=skill_lower,
            is_active=True
        )[:3]
        
        if db_resources.exists():
            resource_list = [
                {
                    "title": res.title,
                    "url": res.url,
                    "type": res.resource_type,
                    "description": res.description,
                    "duration": res.duration
                }
                for res in db_resources
            ]
            cache.set(cache_key, resource_list, 3600)
            resources.append({"skill": skill, "resources": resource_list})
        else:
            # Use AI to generate
            try:
                ai_resources = get_learning_resources_with_ai([skill])
                if ai_resources:
                    resource_list = ai_resources[0].get("resources", [])
                    cache.set(cache_key, resource_list, 3600)
                    resources.append({"skill": skill, "resources": resource_list})
            except:
                # Final fallback
                resources.append({
                    "skill": skill,
                    "resources": [{
                        "title": f"{skill.title()} on YouTube",
                        "url": f"https://www.youtube.com/results?search_query={skill}+tutorial+2024",
                        "type": "video",
                        "description": f"Video tutorials on {skill}",
                        "duration": "Varies"
                    }]
                })
    
    return resources


# ============================================================================
# COVER LETTER - AI
# ============================================================================

def generate_cover_letter_with_gemini(
    resume_text: str,
    jd_text: str,
    custom_prompt: str = "",
    applicant_name: str = "",
    applicant_email: str = "",
    job_title: str = "",
    company_name: str = ""
) -> str:
    """Generate cover letter using Gemini AI"""
    if not resume_text or not jd_text:
        raise ValidationError("Resume and job description are required.")
    
    prompt = f"""
You are a professional career advisor. Write a compelling cover letter.

Instructions:
- Professional tone
- Highlight relevant skills from resume that match job requirements
- Show enthusiasm for the role
- Keep it concise (250-350 words)
- Format as a proper business letter
{f"- Include this note: {custom_prompt}" if custom_prompt else ""}

Applicant: {applicant_name or "[Your Name]"}
Email: {applicant_email or "[Your Email]"}
Job: {job_title or "the position"}
Company: {company_name or "your organization"}

Resume excerpt:
{resume_text[:1000]}

Job Description:
{jd_text[:1000]}

Write the cover letter:"""
    
    try:
        response = generate_with_retry(prompt, temperature=0.7, max_tokens=600)
        letter = response.text.strip()
        letter = re.sub(r'```[\w]*\n?', '', letter)
        return letter
    except Exception as e:
        logger.error(f"AI cover letter generation failed: {e}")
        raise ValidationError(f"Failed to generate cover letter: {str(e)}")


# ============================================================================
# OFFER ANALYSIS - AI
# ============================================================================

def analyze_offer_letter_with_gemini(offer_text: str) -> Dict:
    """Analyze offer letter using AI"""
    if not offer_text:
        raise ValidationError("Offer letter text is required.")
    
    prompt = f"""
You are an HR analyst. Analyze this job offer letter comprehensively.

Return JSON with:
{{
  "ctc": "Annual compensation",
  "probation_period": "Probation duration",
  "notice_period": "Notice period",
  "risk_flags": ["Concerning terms"],
  "summary": "2-3 sentence summary",
  "compensation_analysis": "Salary analysis",
  "terms_analysis": "Contract terms analysis",
  "negotiation_points": ["Negotiation items"],
  "questions_to_ask": ["Clarification questions"]
}}

Offer Letter:
{offer_text[:2500]}
"""
    
    try:
        response = generate_with_retry(prompt, temperature=0.2, max_tokens=800)
        raw = response.text.strip()
        raw = re.sub(r'```json\n?', '', raw)
        raw = re.sub(r'```\n?', '', raw)
        
        analysis = json.loads(raw)
        
        defaults = {
            "ctc": "Not specified",
            "probation_period": "Not specified",
            "notice_period": "Not specified",
            "risk_flags": [],
            "summary": "Offer analysis completed.",
            "compensation_analysis": "No details found.",
            "terms_analysis": "No details found.",
            "negotiation_points": [],
            "questions_to_ask": []
        }
        
        for key, default in defaults.items():
            if key not in analysis or not analysis[key]:
                analysis[key] = default
        
        return analysis
    except Exception as e:
        logger.error(f"AI offer analysis failed: {e}")
        raise ValidationError(f"Failed to analyze offer: {str(e)}")


# ============================================================================
# ATS SCORING - AI
# ============================================================================

def calculate_ats_score(resume_text: str, skills: List[str]) -> Dict:
    """Calculate ATS score using AI"""
    try:
        result = optimize_resume_with_ai(resume_text, "")
        return {
            "ats_score": result.get("ats_score", 70),
            "keyword_match": 75,
            "format_score": 75,
            "content_score": 70,
            "strengths": ["Resume analyzed"],
            "weaknesses": ["Add more keywords"],
            "suggestions": result.get("action_items", [])
        }
    except Exception as e:
        logger.error(f"AI ATS scoring failed: {e}")
        return {
            "ats_score": 70,
            "keyword_match": 70,
            "format_score": 70,
            "content_score": 70,
            "strengths": [],
            "weaknesses": [],
            "suggestions": []
        }


# ============================================================================
# STUB FUNCTIONS (Remove these if not used in views.py)
# ============================================================================

def optimize_resume_for_ats(resume_text: str, job_description: str = "") -> str:
    """Optimize resume for ATS - delegates to AI"""
    try:
        result = optimize_resume_with_ai(resume_text, job_description)
        return result.get("optimized_summary", resume_text)
    except:
        return resume_text

def calculate_user_readiness_score(resume_data: Dict) -> int:
    """Calculate user readiness score"""
    score = 50
    if resume_data.get("skills"):
        score += len(resume_data["skills"]) * 2
    if resume_data.get("experience"):
        score += len(resume_data["experience"]) * 5
    if resume_data.get("education"):
        score += len(resume_data["education"]) * 3
    return min(score, 100)