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

# Configure Gemini - Load from Django settings (which loads from .env)
try:
    API_KEY = settings.GEMINI_API_KEY
except AttributeError:
    raise ImproperlyConfigured(
        "GEMINI_API_KEY not found in settings. "
        "Ensure it's defined in .env and loaded in settings.py"
    )

if not API_KEY or API_KEY == "your-gemini-api-key-here":
    raise ImproperlyConfigured(
        "Gemini API key not configured properly. "
        "Set GEMINI_API_KEY in .env file"
    )

genai.configure(api_key=API_KEY)

try:
    GEMINI_MODEL = settings.GEMINI_MODEL
except AttributeError:
    GEMINI_MODEL = "gemini-2.0-flash-exp"
    logger.warning(f"GEMINI_MODEL not in settings, using default: {GEMINI_MODEL}")

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
    """
    if not resume_skills or not jd_text:
        logger.warning("Empty input for fallback job fit")
        return (0.0, [], [])
    
    # Normalize inputs
    jd_lower = jd_text.lower()
    resume_skills_lower = [s.lower().strip() for s in resume_skills if s and s.strip()]
    
    logger.info(f"🔍 Analyzing resume skills: {resume_skills_lower}")
    
    # ✅ Extract skills from JD using multiple methods
    jd_skills = set()
    
    # Method 1: Use skill patterns
    for pattern in SKILL_PATTERNS:
        try:
            matches = re.findall(pattern, jd_lower, re.IGNORECASE)
            if matches:
                for match in matches:
                    if isinstance(match, tuple):
                        skill = next((m for m in match if m and m.strip()), None)
                    else:
                        skill = match
                    
                    if skill:
                        skill = skill.strip().lower()
                        # Normalize
                        skill = skill.replace('.js', '').replace('.py', '').replace('-', ' ').strip()
                        if skill and skill not in SKILL_BLACKLIST and len(skill) > 1:
                            jd_skills.add(skill)
        except Exception as e:
            logger.error(f"Error matching pattern: {e}")
            continue
    
    # Method 2: Extract multi-word technical terms
    tech_terms = [
        'machine learning', 'deep learning', 'computer vision', 'natural language processing',
        'web development', 'mobile development', 'full stack', 'full-stack', 'fullstack',
        'front end', 'frontend', 'front-end', 'back end', 'backend', 'back-end',
        'cloud computing', 'distributed systems', 'version control', 'continuous integration',
        'continuous deployment', 'test driven development', 'agile methodology'
    ]
    
    for term in tech_terms:
        if term in jd_lower:
            jd_skills.add(term)
    
    # Method 3: Direct skill name search (case-insensitive)
    # Check if any resume skill appears directly in JD
    for resume_skill in resume_skills_lower:
        if resume_skill in jd_lower:
            jd_skills.add(resume_skill)
    
    logger.info(f"📊 Extracted {len(jd_skills)} skills from JD: {sorted(list(jd_skills))[:20]}")
    
    # ✅ Improved matching with better fuzzy logic
    matching_skills = []
    matched_jd_skills = set()
    
    for resume_skill in resume_skills_lower:
        if not resume_skill or resume_skill in SKILL_BLACKLIST:
            continue
        
        # Clean for comparison
        resume_skill_clean = resume_skill.replace('.', '').replace('-', '').replace('_', '').replace(' ', '').strip()
        
        matched = False
        for jd_skill in jd_skills:
            if jd_skill in matched_jd_skills:
                continue
            
            jd_skill_clean = jd_skill.replace('.', '').replace('-', '').replace('_', '').replace(' ', '').strip()
            
            # 1. Exact match (case-insensitive)
            if resume_skill == jd_skill:
                original_skill = resume_skills[resume_skills_lower.index(resume_skill)]
                matching_skills.append(original_skill)
                matched_jd_skills.add(jd_skill)
                logger.info(f"✅ Exact: '{original_skill}' = '{jd_skill}'")
                matched = True
                break
            
            # 2. Direct substring match (python in "python developer")
            elif jd_skill in resume_skill or resume_skill in jd_skill:
                original_skill = resume_skills[resume_skills_lower.index(resume_skill)]
                matching_skills.append(original_skill)
                matched_jd_skills.add(jd_skill)
                logger.info(f"✅ Substring: '{original_skill}' ~ '{jd_skill}'")
                matched = True
                break
            
            # 3. Cleaned match (javascript = js)
            elif jd_skill_clean in resume_skill_clean or resume_skill_clean in jd_skill_clean:
                original_skill = resume_skills[resume_skills_lower.index(resume_skill)]
                matching_skills.append(original_skill)
                matched_jd_skills.add(jd_skill)
                logger.info(f"✅ Partial: '{original_skill}' ~ '{jd_skill}'")
                matched = True
                break
            
            # 4. Known aliases
            elif are_skill_aliases(resume_skill, jd_skill):
                original_skill = resume_skills[resume_skills_lower.index(resume_skill)]
                matching_skills.append(original_skill)
                matched_jd_skills.add(jd_skill)
                logger.info(f"✅ Alias: '{original_skill}' = '{jd_skill}'")
                matched = True
                break
        
        # ✅ NEW: If skill not matched but appears anywhere in JD text, count it
        if not matched and resume_skill in jd_lower:
            original_skill = resume_skills[resume_skills_lower.index(resume_skill)]
            matching_skills.append(original_skill)
            logger.info(f"✅ Text match: '{original_skill}' found in JD")
    
    # Find missing skills (JD skills not in resume)
    missing_skills = []
    for jd_skill in jd_skills:
        if jd_skill in matched_jd_skills or jd_skill in SKILL_BLACKLIST:
            continue
        
        # Check if resume has this skill (case-insensitive)
        found = False
        for resume_skill in resume_skills_lower:
            if (jd_skill in resume_skill or resume_skill in jd_skill or 
                are_skill_aliases(jd_skill, resume_skill)):
                found = True
                break
        
        if not found:
            # Capitalize for display
            if len(jd_skill) <= 3 or jd_skill.isupper():
                missing_skills.append(jd_skill.upper())
            else:
                missing_skills.append(jd_skill.title())
    
    # Remove duplicates
    matching_skills = list(dict.fromkeys(matching_skills))
    missing_skills = list(dict.fromkeys(missing_skills))
    
    logger.info(f"🎯 Final Matching ({len(matching_skills)}): {matching_skills}")
    logger.info(f"⚠️ Final Missing ({len(missing_skills)}): {missing_skills[:10]}")
    
    # ✅ Better scoring algorithm
    total_skills_mentioned = len(jd_skills)
    
    if total_skills_mentioned == 0:
        # No specific tech skills in JD - check general skill count
        if len(resume_skills) >= 5:
            fit_score = 75.0
        elif len(resume_skills) >= 3:
            fit_score = 60.0
        else:
            fit_score = 40.0
    else:
        # Calculate based on coverage
        matched_count = len(matched_jd_skills)
        coverage_ratio = matched_count / total_skills_mentioned
        
        # Base score from coverage (0-70%)
        base_score = coverage_ratio * 70
        
        # Bonus for having many matching skills (0-20%)
        bonus_score = min(len(matching_skills) * 3, 20)
        
        # Bonus for having extra skills not in JD (0-10%)
        extra_skills = len(resume_skills) - len(matching_skills)
        extra_bonus = min(extra_skills * 2, 10)
        
        fit_score = base_score + bonus_score + extra_bonus
        fit_score = min(fit_score, 95.0)
    
    fit_score = round(fit_score, 1)
    
    logger.info(f"📈 Final fit score: {fit_score}% ({len(matching_skills)} matched / {total_skills_mentioned} required)")
    
    return (
        fit_score,
        matching_skills[:25],
        missing_skills[:15]
    )


def are_skill_aliases(skill1: str, skill2: str) -> bool:
    """Check if two skills are aliases/variations of each other"""
    aliases = {
        # Languages
        'js': ['javascript', 'ecmascript', 'es6', 'es2015'],
        'ts': ['typescript'],
        'py': ['python', 'python3'],
        
        # Frameworks
        'node': ['nodejs', 'node.js', 'node js'],
        'react': ['reactjs', 'react.js', 'react js'],
        'angular': ['angularjs', 'angular.js', 'angular js'],
        'vue': ['vuejs', 'vue.js', 'vue js'],
        'django': ['django rest', 'django rest framework', 'drf'],
        
        # Databases
        'postgres': ['postgresql', 'psql'],
        'mongo': ['mongodb', 'mongo db'],
        'mysql': ['my sql'],
        
        # Cloud
        'aws': ['amazon web services', 'amazon aws'],
        'gcp': ['google cloud', 'google cloud platform'],
        'azure': ['microsoft azure', 'ms azure'],
        'k8s': ['kubernetes', 'kube'],
        
        # DevOps
        'ci/cd': ['continuous integration', 'continuous deployment', 'cicd'],
        'docker': ['containerization', 'containers'],
        
        # AI/ML
        'ml': ['machine learning'],
        'dl': ['deep learning'],
        'nlp': ['natural language processing', 'natural language'],
        'cv': ['computer vision'],
        
        # General
        'api': ['rest', 'restful', 'rest api', 'restful api'],
        'sql': ['mysql', 'postgresql', 'sql server', 'database'],
        'fullstack': ['full stack', 'full-stack'],
        'frontend': ['front end', 'front-end'],
        'backend': ['back end', 'back-end'],
    }
    
    s1 = skill1.lower().strip()
    s2 = skill2.lower().strip()
    
    # Direct equality
    if s1 == s2:
        return True
    
    # Check aliases
    for key, values in aliases.items():
        # If both are in the same alias group
        if (s1 == key or s1 in values) and (s2 == key or s2 in values):
            return True
    
    # Check if one contains the other (min 3 chars)
    if len(s1) >= 3 and len(s2) >= 3:
        if s1 in s2 or s2 in s1:
            return True
    
    return False


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
        
        # ✅ Fix cache key - replace spaces with underscores
        cache_key = f"learning_resources_{skill_lower.replace(' ', '_').replace('-', '_')}"
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
    
    # ✅ SIMPLIFIED prompt - gets to the point faster
    prompt = f"""Write a professional cover letter for this job application. Use business letter format with 3-4 paragraphs (300-400 words total).

**Applicant:** {applicant_name or "[Your Name]"}
**Email:** {applicant_email or "[Your Email]"}
**Position:** {job_title}
**Company:** {company_name}

**Resume Summary:**
{resume_text[:600]}

**Job Description:**
{jd_text[:600]}

{f"**Special Instructions:** {custom_prompt}" if custom_prompt else ""}

**Letter Requirements:**
1. Opening: Express enthusiasm for the {job_title} role
2. Body paragraph 1: Highlight 2-3 matching skills with examples
3. Body paragraph 2: Show company knowledge and culture fit
4. Closing: Request interview, thank reader, professional sign-off

Write the complete letter now:"""
    
    try:
        response = generate_with_retry(prompt, temperature=0.7, max_tokens=2000)
        letter = response.text.strip()
        
        # Remove markdown code fences
        letter = re.sub(r'```[\w]*\n?', '', letter)
        letter = re.sub(r'```\n?', '', letter)
        
        # Check length
        word_count = len(letter.split())
        logger.info(f"Generated cover letter: {word_count} words")
        
        if word_count < 50:
            raise ValueError(f"Letter too short: {word_count} words")
        
        return letter
        
    except Exception as e:
        logger.error(f"Cover letter generation failed: {e}")
        raise ValidationError(f"Failed to generate cover letter: {str(e)}")


# ============================================================================
# OFFER ANALYSIS - AI
# ============================================================================

def analyze_offer_letter_with_gemini(offer_text: str) -> Dict:
    """Analyze offer letter using AI with robust JSON parsing"""
    if not offer_text:
        raise ValidationError("Offer letter text is required.")
    
    # ✅ IMPROVED: More explicit JSON requirements
    prompt = f"""
Analyze this job offer letter and extract key information.

You MUST respond with ONLY valid JSON in this exact format (no explanations before or after):

{{
  "ctc": "Annual salary amount with currency",
  "probation_period": "Duration in months",
  "notice_period": "Duration in days/months",
  "risk_flags": ["List of concerning terms found"],
  "explanation": "Brief 2-3 sentence summary of the offer",
  "compensation_analysis": "Analysis of salary, bonuses, benefits",
  "terms_analysis": "Analysis of employment terms and conditions",
  "negotiation_points": ["List of items you could negotiate"],
  "questions_to_ask": ["List of clarifying questions to ask employer"]
}}

RULES:
1. Return ONLY the JSON object, no markdown, no code fences, no explanations
2. All string values must be in quotes
3. All arrays must contain at least one item or be empty []
4. If information is missing, use "Not specified" for strings or [] for arrays
5. Keep all text concise and professional

Offer Letter Text (first 2000 chars):
{offer_text[:2000]}

JSON Response:"""
    
    try:
        response = generate_with_retry(prompt, temperature=0.1, max_tokens=1500, max_retries=2)
        raw = response.text.strip()
        
        logger.info(f"Raw AI response (first 200 chars): {raw[:200]}")
        
        # ✅ IMPROVED: Better cleaning of response
        # Remove markdown code fences
        raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
        raw = re.sub(r'\s*```$', '', raw, flags=re.MULTILINE)
        
        # Remove any text before first {
        json_start = raw.find('{')
        if json_start > 0:
            raw = raw[json_start:]
        
        # Remove any text after last }
        json_end = raw.rfind('}')
        if json_end > 0:
            raw = raw[:json_end + 1]
        
        logger.info(f"Cleaned response (first 200 chars): {raw[:200]}")
        
        # Try to parse JSON
        try:
            analysis = json.loads(raw)
        except json.JSONDecodeError as je:
            logger.error(f"JSON parsing failed at position {je.pos}: {je.msg}")
            logger.error(f"Problematic section: ...{raw[max(0, je.pos-50):je.pos+50]}...")
            
            # ✅ FALLBACK: Try to extract data with regex
            logger.warning("Falling back to regex extraction")
            analysis = _extract_offer_data_with_regex(offer_text)
        
        # ✅ Ensure all required fields exist with proper defaults
        defaults = {
            "ctc": "Not specified",
            "probation_period": "Not specified", 
            "notice_period": "Not specified",
            "risk_flags": [],
            "explanation": "Offer letter has been uploaded and is ready for review.",
            "compensation_analysis": "Unable to extract detailed compensation information.",
            "terms_analysis": "Unable to extract detailed terms and conditions.",
            "negotiation_points": ["Request clarification on any unclear terms"],
            "questions_to_ask": ["What are the performance evaluation criteria?", "What benefits are included?"]
        }
        
        for key, default in defaults.items():
            if key not in analysis or not analysis[key]:
                analysis[key] = default
        
        logger.info(f"✅ Offer analysis complete: CTC={analysis['ctc']}, Risks={len(analysis['risk_flags'])}")
        return analysis
        
    except Exception as e:
        logger.error(f"AI offer analysis failed completely: {e}", exc_info=True)
        # ✅ Return fallback analysis instead of raising error
        return _extract_offer_data_with_regex(offer_text)


def _extract_offer_data_with_regex(offer_text: str) -> Dict:
    """
    Fallback: Extract basic offer data using regex patterns
    """
    logger.info("📋 Using regex-based offer extraction")
    
    analysis = {
        "ctc": "Not specified",
        "probation_period": "Not specified",
        "notice_period": "Not specified",
        "risk_flags": [],
        "explanation": "Basic offer information extracted.",
        "compensation_analysis": "No detailed compensation analysis available.",
        "terms_analysis": "No detailed terms analysis available.",
        "negotiation_points": [],
        "questions_to_ask": []
    }
    
    text_lower = offer_text.lower()
    
    # Extract CTC/Salary
    ctc_patterns = [
        r'(?:ctc|salary|compensation|annual package)[\s:]+(?:is\s+)?(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d+)?)\s*(?:lpa|lakhs?|per annum|annually)?',
        r'(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d+)?)\s*(?:lpa|lakhs?|per annum)',
        r'([\d,]+(?:\.\d+)?)\s*(?:lpa|lakhs? per annum)',
    ]
    for pattern in ctc_patterns:
        match = re.search(pattern, text_lower)
        if match:
            amount = match.group(1).replace(',', '')
            analysis['ctc'] = f"₹{amount} LPA"
            break
    
    # Extract Probation Period
    probation_patterns = [
        r'probation(?:ary)?\s+period[\s:]+(?:of\s+)?([\d]+)\s*(months?|days?)',
        r'([\d]+)\s*months?\s+probation',
    ]
    for pattern in probation_patterns:
        match = re.search(pattern, text_lower)
        if match:
            duration = match.group(1)
            unit = match.group(2) if len(match.groups()) > 1 else 'months'
            analysis['probation_period'] = f"{duration} {unit}"
            break
    
    # Extract Notice Period
    notice_patterns = [
        r'notice\s+period[\s:]+(?:of\s+)?([\d]+)\s*(months?|days?)',
        r'([\d]+)\s*(?:months?|days?)\s+notice',
    ]
    for pattern in notice_patterns:
        match = re.search(pattern, text_lower)
        if match:
            duration = match.group(1)
            unit = match.group(2) if len(match.groups()) > 1 else 'days'
            analysis['notice_period'] = f"{duration} {unit}"
            break
    
    # Check for common risk flags
    risk_keywords = [
        ('bond', 'Contains service bond requirement'),
        ('penalty', 'Mentions penalties or fines'),
        ('non-compete', 'Non-compete clause present'),
        ('no paid leave', 'Limited or no paid leave mentioned'),
        ('unpaid', 'Contains unpaid work provisions'),
    ]
    
    for keyword, flag in risk_keywords:
        if keyword in text_lower:
            analysis['risk_flags'].append(flag)
    
    # Generate basic recommendations
    if analysis['ctc'] != "Not specified":
        analysis['compensation_analysis'] = f"The offered CTC is {analysis['ctc']}. Consider researching industry standards for this role."
    
    if analysis['probation_period'] != "Not specified":
        analysis['terms_analysis'] = f"Probation period is {analysis['probation_period']}. "
    if analysis['notice_period'] != "Not specified":
        analysis['terms_analysis'] += f"Notice period is {analysis['notice_period']}."
    
    analysis['negotiation_points'] = [
        "Salary and variable pay components",
        "Work from home policy",
        "Learning and development budget",
        "Health insurance coverage"
    ]
    
    analysis['questions_to_ask'] = [
        "What is the salary breakup (fixed vs variable)?",
        "What are the performance review cycles?",
        "What benefits are included besides salary?",
        "What is the company's work culture like?",
        "Are there opportunities for career growth?"
    ]
    
    logger.info(f"✅ Regex extraction complete: CTC={analysis['ctc']}, Probation={analysis['probation_period']}")
    return analysis

# ============================================================================
# ATS SCORING - AI
# ============================================================================

def calculate_ats_score(resume_text: str, skills: List[str]) -> Dict:
    """Calculate ATS score using AI with detailed analysis"""
    try:
        # ✅ IMPROVED: More detailed prompt for better analysis
        prompt = f"""
Analyze this resume for ATS (Applicant Tracking System) compatibility.

Return ONLY valid JSON in this exact format:
{{
  "ats_score": 75,
  "keyword_match": 80,
  "format_score": 70,
  "content_score": 75,
  "strengths": [
    "Clear skills section with {len(skills)} technical skills",
    "Professional experience with measurable achievements",
    "Clean, ATS-friendly formatting"
  ],
  "weaknesses": [
    "Missing specific metrics in some job descriptions",
    "Could add more industry keywords"
  ],
  "suggestions": [
    "Add quantifiable achievements (e.g., 'Improved performance by 40%')",
    "Include more action verbs at the start of bullet points",
    "Add relevant certifications if available"
  ]
}}

Resume excerpt (first 1200 chars):
{resume_text[:1200]}

Identified Skills: {', '.join(skills[:15])}

Provide specific, actionable feedback based on the actual content."""

        response = generate_with_retry(prompt, temperature=0.3, max_tokens=800, max_retries=2)
        raw = response.text.strip()
        
        # Clean response
        raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
        raw = re.sub(r'\s*```$', '', raw, flags=re.MULTILINE)
        
        # Extract JSON
        json_start = raw.find('{')
        if json_start > 0:
            raw = raw[json_start:]
        json_end = raw.rfind('}')
        if json_end > 0:
            raw = raw[:json_end + 1]
        
        result = json.loads(raw)
        
        # ✅ Validate that we got meaningful data
        if not result.get('strengths') or not result.get('weaknesses'):
            logger.warning("AI returned empty analysis, using enhanced fallback")
            raise ValueError("Insufficient analysis data")
        
        logger.info(f"✅ ATS analysis complete: {result.get('ats_score')}%, {len(result.get('strengths', []))} strengths, {len(result.get('weaknesses', []))} weaknesses")
        return result
        
    except Exception as e:
        logger.error(f"AI ATS scoring failed: {e}, using enhanced fallback")
        return _calculate_ats_score_fallback(resume_text, skills)


def _calculate_ats_score_fallback(resume_text: str, skills: List[str]) -> Dict:
    """Enhanced fallback ATS scoring with detailed analysis"""
    logger.info("📊 Using enhanced fallback ATS scoring")
    
    text_lower = resume_text.lower()
    word_count = len(resume_text.split())
    
    # Calculate scores
    keyword_score = 70
    format_score = 75
    content_score = 70
    
    strengths = []
    weaknesses = []
    suggestions = []
    
    # ✅ ANALYZE SKILLS
    if len(skills) >= 10:
        keyword_score += 15
        strengths.append(f"Strong technical skills section with {len(skills)} skills listed")
    elif len(skills) >= 5:
        keyword_score += 10
        strengths.append(f"Good skills section with {len(skills)} technical skills")
    else:
        keyword_score -= 10
        weaknesses.append(f"Limited skills listed ({len(skills)} found) - add more relevant technical skills")
        suggestions.append("Add more specific technical skills relevant to your target role")
    
    # ✅ ANALYZE CONTACT INFO
    has_email = bool(re.search(EMAIL_PATTERN, resume_text, re.IGNORECASE))
    has_phone = any(re.search(pattern, resume_text) for pattern in PHONE_PATTERNS)
    
    if has_email and has_phone:
        format_score += 10
        strengths.append("Complete contact information provided")
    else:
        format_score -= 15
        weaknesses.append("Missing contact information (email or phone)")
        suggestions.append("Ensure email and phone number are clearly visible at the top")
    
    # ✅ ANALYZE EXPERIENCE SECTION
    experience_keywords = ['experience', 'work history', 'employment', 'professional experience']
    has_experience_section = any(keyword in text_lower for keyword in experience_keywords)
    
    if has_experience_section:
        content_score += 10
        strengths.append("Clear work experience section present")
        
        # Check for quantifiable achievements
        achievement_patterns = [r'\d+%', r'\d+ users', r'\d+ projects', r'increased', r'improved', r'reduced', r'achieved']
        achievements_count = sum(1 for pattern in achievement_patterns if re.search(pattern, text_lower))
        
        if achievements_count >= 3:
            content_score += 10
            strengths.append("Good use of quantifiable achievements")
        else:
            weaknesses.append("Limited quantifiable achievements - add metrics to demonstrate impact")
            suggestions.append("Add numbers and percentages (e.g., 'Improved performance by 40%', 'Managed team of 5')")
    else:
        content_score -= 15
        weaknesses.append("No clear work experience section found")
        suggestions.append("Add a dedicated 'Work Experience' or 'Professional Experience' section")
    
    # ✅ ANALYZE ACTION VERBS
    action_verbs = ['developed', 'created', 'managed', 'led', 'implemented', 'designed', 'built', 'improved', 'optimized', 'delivered']
    action_verb_count = sum(1 for verb in action_verbs if verb in text_lower)
    
    if action_verb_count >= 5:
        content_score += 10
        strengths.append("Strong use of action verbs in descriptions")
    elif action_verb_count < 3:
        weaknesses.append("Limited use of impactful action verbs")
        suggestions.append("Start bullet points with strong action verbs (Developed, Led, Implemented, etc.)")
    
    # ✅ ANALYZE LENGTH
    if 300 <= word_count <= 800:
        format_score += 5
        strengths.append("Resume length is appropriate for ATS parsing")
    elif word_count < 200:
        format_score -= 10
        weaknesses.append("Resume appears too brief - may lack sufficient detail")
        suggestions.append("Expand on your experience and achievements")
    elif word_count > 1000:
        format_score -= 5
        weaknesses.append("Resume may be too lengthy - consider condensing")
        suggestions.append("Focus on most relevant and recent experience")
    
    # ✅ ANALYZE EDUCATION
    if 'education' in text_lower or 'degree' in text_lower or 'university' in text_lower:
        content_score += 5
        strengths.append("Education section included")
    else:
        weaknesses.append("No education section found")
        suggestions.append("Add your educational qualifications")
    
    # ✅ CHECK FOR COMMON ATS ISSUES
    problematic_chars = ['→', '•', '★', '◆']
    if any(char in resume_text for char in problematic_chars):
        format_score -= 5
        weaknesses.append("Special characters detected that may not parse well in ATS")
        suggestions.append("Use standard bullet points (•) and avoid fancy symbols")
    
    # Cap scores
    keyword_score = max(40, min(100, keyword_score))
    format_score = max(40, min(100, format_score))
    content_score = max(40, min(100, content_score))
    
    # Calculate overall score (weighted average)
    overall_score = int((keyword_score * 0.4) + (format_score * 0.3) + (content_score * 0.3))
    
    # ✅ Ensure we always have some content
    if not strengths:
        strengths = ["Resume successfully uploaded and analyzed", f"{len(skills)} technical skills identified"]
    
    if not weaknesses:
        weaknesses = ["Continue to refine and update your resume regularly"]
    
    if not suggestions:
        suggestions = [
            "Keep your resume updated with your latest skills and experience",
            "Tailor your resume for each job application",
            "Use keywords from the job description"
        ]
    
    logger.info(f"✅ Fallback ATS score: {overall_score}% (Keywords: {keyword_score}, Format: {format_score}, Content: {content_score})")
    logger.info(f"   Strengths: {len(strengths)}, Weaknesses: {len(weaknesses)}, Suggestions: {len(suggestions)}")
    
    return {
        "ats_score": overall_score,
        "keyword_match": keyword_score,
        "format_score": format_score,
        "content_score": content_score,
        "strengths": strengths[:10],  # Limit to top 10
        "weaknesses": weaknesses[:8],  # Limit to top 8
        "suggestions": suggestions[:10]  # Limit to top 10
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


# ============================================================================
# ADDITIONAL FUNCTIONS
# ============================================================================

EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

PHONE_PATTERNS = [
    r'\+91[\s-]?\d{10}',
    r'\d{10}',
    r'\+\d{1,3}[\s-]?\d{9,12}'
]

# ✅ IMPROVED: More specific skill patterns with boundaries
SKILL_PATTERNS = [
    # Programming Languages (exact match)
    r'\b(python|java|javascript|typescript|c\+\+|c#|ruby|php|swift|kotlin|scala|rust|golang|go|perl|r|matlab|sql|html|css|bash|shell|powershell)\b',
    
    # Frameworks & Libraries (specific names)
    r'\b(react\.?js|react|angular\.?js|angular|vue\.?js|vue|node\.?js|nodejs|django|flask|fastapi|spring boot|spring|express\.?js|express|laravel|rails|ruby on rails|asp\.net|asp\.net core|next\.?js|nuxt\.?js|svelte|ember\.?js)\b',
    
    # Databases (specific products)
    r'\b(mysql|postgresql|postgres|mongodb|oracle|redis|cassandra|dynamodb|sqlite|mariadb|elasticsearch|neo4j|couchdb|influxdb|clickhouse)\b',
    
    # Cloud & DevOps (major platforms/tools)
    r'\b(aws|amazon web services|azure|microsoft azure|gcp|google cloud|docker|kubernetes|k8s|jenkins|gitlab ci|github actions|terraform|ansible|chef|puppet|ci/cd|circleci|travis ci)\b',
    
    # AI/ML/Data Science
    r'\b(machine learning|deep learning|tensorflow|pytorch|scikit-learn|keras|pandas|numpy|opencv|nltk|spacy|hugging face|transformers|computer vision|nlp|natural language processing)\b',
    
    # Version Control & Collaboration
    r'\b(git|github|gitlab|bitbucket|svn|subversion|jira|confluence|trello|asana|slack)\b',
    
    # Web Technologies
    r'\b(rest|restful|api|graphql|grpc|websocket|http|https|json|xml|ajax|sass|scss|less|tailwind|tailwind css|bootstrap|material-ui|mui|chakra ui|webpack|vite|rollup|babel)\b',
    
    # Mobile Development
    r'\b(react native|flutter|swift|swiftui|kotlin|android|ios|xamarin|ionic|cordova)\b',
    
    # Testing & Quality
    r'\b(jest|mocha|chai|pytest|junit|selenium|cypress|playwright|testing library|unittest|testng)\b',
    
    # Architecture & Patterns
    r'\b(microservices|monolith|serverless|lambda|event-driven|message queue|rabbitmq|kafka|redis pub/sub|websockets|mvc|mvvm|clean architecture)\b',
    
    # Data & Analytics
    r'\b(tableau|power bi|looker|metabase|apache spark|hadoop|hive|airflow|data pipeline|etl)\b',
]

# ✅ Add a blacklist of common non-skill words that often get matched
SKILL_BLACKLIST = {
    'unique', 'approach', 'required', 'connections', 'voices', 'skills', 
    'research', 'backgrounds', 'promote', 'collaboration', 'perspectives', 
    'players', 'deeper', 'dedicated', 'immersive', 'around', 'humanistic', 
    'spaces', 'different', 'team', 'work', 'project', 'develop', 'build',
    'create', 'design', 'manage', 'lead', 'support', 'help', 'assist',
    'provide', 'ensure', 'maintain', 'improve', 'enhance', 'optimize',
    'implement', 'analyze', 'evaluate', 'coordinate', 'communicate',
    'collaborate', 'participate', 'contribute', 'deliver', 'achieve',
    'experience', 'knowledge', 'understanding', 'ability', 'strong',
    'excellent', 'good', 'solid', 'proven', 'demonstrated'
}

def enrich_parsed_resume(parsed_data: Dict, fallback_text: str = "") -> Dict:
    """
    Enrich parsed resume data using regex fallback when AI fails
    
    Args:
        parsed_data: Dictionary with partial resume data
        fallback_text: Raw text to extract from if fields are missing
    
    Returns:
        Enriched dictionary with extracted fields
    """
    import re
    
    text = fallback_text or parsed_data.get('parsed_text', '')
    
    # Extract email if missing
    if not parsed_data.get('email') and text:
        email_match = re.search(EMAIL_PATTERN, text, re.IGNORECASE)
        if email_match:
            parsed_data['email'] = email_match.group(0)
    
    # Extract phone if missing
    if not parsed_data.get('phone') and text:
        for pattern in PHONE_PATTERNS:
            phone_match = re.search(pattern, text)
            if phone_match:
                parsed_data['phone'] = phone_match.group(0)
                break
    
    # Extract name if missing (first line that looks like a name)
    if not parsed_data.get('name') and text:
        name_match = re.search(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})$', text, re.MULTILINE)
        if name_match:
            parsed_data['name'] = name_match.group(1)
    
    # Extract skills if missing or empty
    if not parsed_data.get('skills') or len(parsed_data.get('skills', [])) == 0:
        skills = set()
        for pattern in SKILL_PATTERNS:
            matches = re.findall(pattern, text.lower(), re.IGNORECASE)
            skills.update(matches)
        parsed_data['skills'] = list(skills)[:30]
    
    # Extract education if missing
    if not parsed_data.get('education') or len(parsed_data.get('education', [])) == 0:
        education = re.findall(
            r'(B\.?Tech|M\.?Tech|Bachelor|Master|MBA|MCA|BCA|BSc|MSc).*?(?:University|College|Institute)',
            text,
            re.IGNORECASE
        )
        parsed_data['education'] = education[:5]
    
    # Extract experience if missing (ONLY work experience, NOT education dates)
    if not parsed_data.get('experience') or len(parsed_data.get('experience', [])) == 0:
        # Look for job titles followed by company names
        experience = re.findall(
            r'((?:Software|Senior|Junior|Lead|Principal|Staff)?\s*(?:Engineer|Developer|Analyst|Manager|Architect|Designer|Consultant))\s+(?:at|@|-)\s+([A-Z][a-zA-Z0-9\s&.]+?)(?:\s+(?:from|since|\d{4}))',
            text,
            re.IGNORECASE
        )
        
        experience_list = []
        for title, company in experience[:5]:
            # Clean up company name
            company = company.strip()
            # Remove common suffixes
            company = re.sub(r'\s+(?:pvt|ltd|inc|llc|corp).*$', '', company, flags=re.IGNORECASE)
            experience_list.append(f"{title.strip()} at {company}")
        
        parsed_data['experience'] = experience_list
    
    # Ensure parsed_text is included
    if not parsed_data.get('parsed_text'):
        parsed_data['parsed_text'] = text[:2000]
    
    return parsed_data