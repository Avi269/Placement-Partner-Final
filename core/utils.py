"""
============================================================================
CORE UTILITIES - AI & File Processing Functions
============================================================================
This module contains all utility functions for the placement partner app:

AI-Powered Functions (Using Google Gemini):
- generate_cover_letter_with_gemini: Create personalized cover letters
- analyze_offer_letter_with_gemini: Analyze offer terms and risks
- calculate_job_fit_with_gemini: Calculate resume-job match percentage
- get_learning_resources_with_gemini: Get learning recommendations

File Processing:
- parse_resume_file: Extract text and data from PDF/DOCX resumes
- extract_text_from_file: Generic text extraction
- validate_file_type: Check file types securely
- validate_file_size: Enforce file size limits

Resume Processing:
- extract_skills_from_text: Extract skills using NLP
- optimize_resume_for_ats: Make resumes ATS-friendly
- calculate_ats_score: Score resume ATS compatibility
- enrich_parsed_resume: Enhance extracted data

Skill Analysis:
- extract_experience_keywords: Find experience-related keywords
- calculate_user_readiness_score: Calculate job readiness

All AI functions include retry logic and fallback mechanisms for reliability.
============================================================================
"""

# Standard library imports
import re  # Regular expressions for text parsing
import json  # JSON handling
import os  # File system operations
import logging  # Logging for debugging
from typing import Dict, List, Tuple, Optional  # Type hints
from time import sleep  # Retry delays

# Third-party imports - NLP and document processing
import spacy  # Natural language processing
from pyresparser import ResumeParser  # Resume parsing library
import docx2txt  # Extract text from DOCX files
from pdf2image import convert_from_path  # Convert PDF to images
import pytesseract  # OCR for scanned PDFs
from pdfminer.high_level import extract_text  # Extract text from PDFs

# Django imports
from django.conf import settings  # Access Django settings
from django.core.exceptions import ValidationError, ImproperlyConfigured  # Django exceptions

# AI library
import google.generativeai as genai  # Google Gemini AI

# ============================================================================
# CONFIGURATION
# ============================================================================

# Configure logging for debugging
logger = logging.getLogger(__name__)

# === GEMINI AI CONFIGURATION ===
# Get API key from environment variables
API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ImproperlyConfigured(
        "Gemini API key not found. Please set GEMINI_API_KEY in your .env file.\n"
        "Get your API key from: https://makersuite.google.com/app/apikey"
    )

# Configure Gemini with API key
genai.configure(api_key=API_KEY)
# Model name can be configured via environment variable
# Default: gemini-2.0-flash (fast, high-quality responses)
# Other options: gemini-1.5-pro, gemini-1.5-flash
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# === FILE VALIDATION CONFIGURATION ===
# Try to import python-magic for secure file type detection
MAGIC_AVAILABLE = False
try:
    import magic  # Check MIME types using magic numbers
    MAGIC_AVAILABLE = True
except ImportError:
    # Fall back to extension-based validation if magic not available
    pass

# === NLP CONFIGURATION ===
# Load spaCy English language model for skill extraction
try:
    NLP = spacy.load("en_core_web_sm")  # Small English model
except OSError:
    raise ImproperlyConfigured(
        "spaCy English model not found. Install it with: python -m spacy download en_core_web_sm"
    )

# ============================================================================
# FILE VALIDATION FUNCTIONS
# ============================================================================

def validate_file_type(file_path: str, allowed_types: Optional[List[str]] = None) -> bool:
    """Validate file type using magic numbers or extension"""
    allowed_types = allowed_types or getattr(settings, 'ALLOWED_FILE_TYPES', ['pdf', 'docx', 'doc', 'txt'])
    
    try:
        file_extension = os.path.splitext(file_path)[1][1:].lower()
        
        if not MAGIC_AVAILABLE:
            return file_extension in allowed_types
        
        # Use magic for MIME type validation
        mime = magic.from_file(file_path, mime=True)
        
        # MIME type mapping
        valid_mime_types = {
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'doc': 'application/msword',
            'txt': 'text/plain'
        }
        
        return (file_extension in allowed_types and 
                mime == valid_mime_types.get(file_extension))
    except Exception:
        return False

def validate_file_size(file_path: str, max_size: Optional[int] = None) -> bool:
    """Validate file size"""
    max_size = max_size or getattr(settings, 'MAX_UPLOAD_SIZE', 10 * 1024 * 1024)  # 10MB
    
    try:
        return os.path.getsize(file_path) <= max_size
    except Exception:
        return False

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent security issues"""
    filename = os.path.basename(filename)
    return re.sub(r'[^\w\-_\.]', '', filename)

def generate_with_retry(prompt: str, max_retries: int = 3, temperature: float = 0.7, max_tokens: int = 512):
    """Helper function with retry logic for Gemini API calls"""
    for attempt in range(max_retries):
        try:
            # Use Gemini API directly
            import google.generativeai as genai
            model = genai.GenerativeModel(GEMINI_MODEL)
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            response = model.generate_content(prompt, generation_config=generation_config)
            
            # Check for empty or None response
            if not response or not hasattr(response, 'text') or not response.text:
                if attempt < max_retries - 1:
                    logger.warning(f"Empty response from Gemini API, retrying... (attempt {attempt + 1}/{max_retries})")
                    sleep(2 ** attempt)
                    continue
                raise ValueError("Empty response from API after all retries")
            
            return response
        except Exception as e:
            if attempt == max_retries - 1:
                raise ValidationError(f"AI generation failed after {max_retries} attempts: {str(e)}")
            logger.warning(f"API call failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
            sleep(2 ** attempt)  # Exponential backoff

def generate_cover_letter_fallback(
    resume_text: str,
    jd_text: str,
    custom_prompt: str = "",
    applicant_name: str = "",
    applicant_email: str = "",
    job_title: str = "",
    company_name: str = ""
) -> str:
    """Generate a cover letter using template-based approach (fallback when AI is unavailable)."""
    import re
    from datetime import datetime
    
    # Extract key information from resume
    resume_skills = []
    resume_experience = []
    
    # Simple skill extraction
    common_skills = ['python', 'java', 'javascript', 'django', 'react', 'sql', 'aws', 'docker', 
                     'machine learning', 'data analysis', 'project management', 'communication']
    for skill in common_skills:
        if skill.lower() in resume_text.lower():
            resume_skills.append(skill.title())
    
    # Use provided values or defaults
    name = applicant_name or "[Your Name]"
    email = applicant_email or "[Your Email]"
    job = job_title or "this position"
    company = company_name or "your esteemed organization"
    
    # Build the cover letter
    date_str = datetime.now().strftime("%B %d, %Y")
    
    cover_letter = f"""{name}
{email}

{date_str}

Hiring Manager
{company}

Dear Hiring Manager,

I am writing to express my strong interest in the {job} position at {company}. After carefully reviewing the job description, I am confident that my background and skills align well with your requirements.

With my experience and expertise in {', '.join(resume_skills[:5]) if resume_skills else 'various technologies'}, I believe I would be a valuable addition to your team. Throughout my career, I have consistently demonstrated my ability to deliver high-quality results and contribute to organizational success.

Key highlights of my qualifications include:

• Strong technical proficiency in {', '.join(resume_skills[:3]) if resume_skills else 'relevant technologies'}
• Proven track record of successful project delivery and problem-solving
• Excellent communication and collaboration skills
• Passion for continuous learning and professional development

I am particularly excited about this opportunity because it aligns perfectly with my career goals and offers the chance to work on challenging and impactful projects. I am confident that my skills and enthusiasm would make me a strong contributor to your team.

{custom_prompt if custom_prompt else 'I am eager to bring my expertise and dedication to your organization and contribute to its continued success.'}

Thank you for considering my application. I look forward to the opportunity to discuss how my background, skills, and enthusiasm align with your needs. I am available for an interview at your convenience.

Sincerely,
{name}

---
Note: This cover letter was generated using a template-based approach. Please review and personalize it based on your specific experience and the job requirements."""
    
    return cover_letter

def generate_cover_letter_with_gemini(
    resume_text: str,
    jd_text: str,
    custom_prompt: str = "",
    applicant_name: str = "",
    applicant_email: str = "",
    job_title: str = "",
    company_name: str = ""
) -> str:
    """Generate a cover letter using Gemini model with fallback."""
    if not resume_text or not jd_text:
        raise ValidationError("Both resume text and job description are required.")
    
    try:
        prompt = (
            "You are a professional career assistant. Generate a compelling, tailored cover letter.\n"
            "Return ONLY the cover letter text without any markdown formatting, code blocks, or commentary.\n\n"
            f"Resume excerpt:\n{resume_text[:1000]}\n\n"
            f"Job Description excerpt:\n{jd_text[:1000]}\n\n"
            f"Additional instructions: {custom_prompt[:500]}"
        )
        
        response = generate_with_retry(
            prompt,
            temperature=0.7,
            max_tokens=512
        )
        
        response_text = response.text.strip()
        
        # Remove markdown code blocks if present
        if '```' in response_text:
            lines = response_text.split('\n')
            cleaned_lines = []
            in_code_block = False
            
            for line in lines:
                if line.strip().startswith('```'):
                    in_code_block = not in_code_block
                    continue
                if not in_code_block:
                    cleaned_lines.append(line)
            
            response_text = '\n'.join(cleaned_lines).strip()
        
        # Remove AI commentary/preamble (common patterns)
        preamble_patterns = [
            "Okay, let's",
            "Here's a",
            "Here is a",
            "I've crafted",
            "I've generated",
            "Below is",
            "This is a"
        ]
        
        for pattern in preamble_patterns:
            if response_text.lower().startswith(pattern.lower()):
                # Find the first line that looks like letter content
                lines = response_text.split('\n')
                for i, line in enumerate(lines):
                    # Look for typical cover letter start patterns
                    if (line.strip().startswith('[') or 
                        'Dear' in line or 
                        line.strip().startswith('Dear') or
                        (i > 0 and len(line.strip()) > 20)):
                        response_text = '\n'.join(lines[i:]).strip()
                        break
                break
        
        return response_text
    except Exception as e:
        logger.warning(f"AI cover letter generation failed: {str(e)}")
        logger.info("Using fallback template-based cover letter generation...")
        return generate_cover_letter_fallback(resume_text, jd_text, custom_prompt, applicant_name, applicant_email, job_title, company_name)

def analyze_offer_letter_with_gemini(offer_text: str) -> Dict:
    """Analyze an offer letter and extract structured data."""
    if not offer_text:
        raise ValidationError("Offer letter text is required.")
    
    # Define default structure for all required fields
    default_result = {
        "ctc": "Not detected",
        "probation_period": "Not detected",
        "notice_period": "Not detected",
        "risk_flags": [],
        "summary": "Analysis completed.",
        "compensation_analysis": "Not available.",
        "terms_analysis": "Not available.",
        "negotiation_points": [],
        "questions_to_ask": []
    }
    
    try:
        prompt = (
            "You are an HR analyst AI. Carefully analyze this job offer letter and return ONLY valid JSON with the following keys:\n"
            "- ctc (string): The Cost to Company or salary amount\n"
            "- probation_period (string): Duration of probation period\n"
            "- notice_period (string): Required notice period\n"
            "- risk_flags (list of strings): Concerning terms or red flags\n"
            "- summary (string): 2-3 sentence summary of the offer\n"
            "- compensation_analysis (string): Analysis of salary, benefits, and market fairness\n"
            "- terms_analysis (string): Analysis of working conditions, legal terms, etc.\n"
            "- negotiation_points (list of strings): 3-5 terms that could be negotiated\n"
            "- questions_to_ask (list of strings): 3-5 important clarification questions\n\n"
            f"Offer Letter:\n{offer_text[:2000]}"
        )
        
        response = generate_with_retry(
            prompt,
            temperature=0.2,
            max_tokens=600
        )

        # Remove ```json code block wrapper if present
        raw = response.text.strip()
        if raw.startswith("```"):
            lines = raw.splitlines()
            # Find the start and end of JSON content
            start_idx = 0
            end_idx = len(lines)
            for i, line in enumerate(lines):
                if line.strip().startswith("```"):
                    if start_idx == 0:
                        start_idx = i + 1
                    else:
                        end_idx = i
                        break
            raw = "\n".join(lines[start_idx:end_idx]).strip()

        result = json.loads(raw)
        
        # Merge with defaults to ensure all fields exist
        for key, default_value in default_result.items():
            if key not in result or result[key] is None or result[key] == "":
                result[key] = default_value
            # Ensure lists are actually lists
            elif key in ['risk_flags', 'negotiation_points', 'questions_to_ask']:
                if not isinstance(result[key], list):
                    result[key] = default_value
        
        return result

    except json.JSONDecodeError as e:
        # Fallback to default structure if JSON parsing fails
        return {
            **default_result,
            "risk_flags": ["Could not analyze offer letter due to format issues."],
            "summary": "The system was unable to extract structured details from the offer letter."
        }

    except Exception as e:
        raise ValidationError(f"Failed to analyze offer letter: {str(e)}")

def calculate_job_fit_with_fallback(
    resume_skills: List[str],
    jd_text: str
) -> Tuple[float, List[str], List[str]]:
    """Calculate job fit using keyword matching (fallback when AI fails)."""
    if not resume_skills or not jd_text:
        return (0.0, [], [])
    
    # Extract skills from job description
    jd_skills = extract_skills_from_text(jd_text)
    
    # Normalize skills for comparison
    resume_skills_lower = set([s.lower().strip() for s in resume_skills if s])
    jd_skills_lower = set([s.lower().strip() for s in jd_skills if s])
    
    # Find matching skills
    matching_skills = list(resume_skills_lower.intersection(jd_skills_lower))
    
    # Find missing skills
    missing_skills = list(jd_skills_lower - resume_skills_lower)
    
    # Calculate fit score
    if len(jd_skills_lower) > 0:
        fit_score = (len(matching_skills) / len(jd_skills_lower)) * 100
    else:
        fit_score = 50.0  # Default if no skills found in JD
    
    # Cap score at 100
    fit_score = min(fit_score, 100.0)
    
    logger.info(f"Fallback job fit: score={fit_score:.1f}, matching={len(matching_skills)}, missing={len(missing_skills)}")
    
    return (fit_score, matching_skills[:10], missing_skills[:10])

def calculate_job_fit_with_gemini(
    resume_skills: List[str],
    jd_text: str
) -> Tuple[float, List[str], List[str]]:
    """Let Gemini analyze job fit based on raw JD and resume skills."""
    try:
        prompt = f"""
You are an expert in HR skill analysis.

Compare the following resume skills with the provided job description.
Return JSON with:
- fit_score (0–100),
- matching_skills (list of strings),
- missing_skills (list of strings)

Resume Skills:
{resume_skills}

Job Description:
{jd_text}
"""
        response = generate_with_retry(
            prompt,
            temperature=0.0,
            max_tokens=300
        )

        raw = response.text.strip()

        if raw.startswith("```") and raw.endswith("```"):
            lines = raw.splitlines()
            raw = "\n".join(lines[1:-1]).strip()

        data = json.loads(raw)

        return (
            float(data.get("fit_score", 0)),
            data.get("matching_skills", []),
            data.get("missing_skills", [])
        )
    except Exception as e:
        # Fallback to keyword-based matching
        logger.warning(f"AI job fit calculation failed: {str(e)}")
        logger.info("Using fallback keyword-based matching...")
        return calculate_job_fit_with_fallback(resume_skills, jd_text)

def get_basic_learning_resources(missing_skills: List[str]) -> List[Dict]:
    """Generate detailed learning resources for missing skills (fallback)."""
    cleaned_skills = [s.lower().strip() for s in missing_skills if s]
    if not cleaned_skills:
        return []
    
    # Map of common skills to real learning resources with detailed descriptions
    resource_map = {
        "python": [
            {"title": "Python.org Official Tutorial", "url": "https://docs.python.org/3/tutorial/", "type": "tutorial", 
             "description": "Comprehensive introduction to Python by the core team. Start here for fundamentals.", "duration": "10-15 hours"},
            {"title": "Real Python - Python Basics", "url": "https://realpython.com/", "type": "course",
             "description": "In-depth tutorials covering Python fundamentals, web development, data science and more.", "duration": "Self-paced"},
            {"title": "Automate the Boring Stuff", "url": "https://automatetheboringstuff.com/", "type": "book",
             "description": "Practical Python for beginners. Learn by automating real-world tasks.", "duration": "20-30 hours"}
        ],
        "django": [
            {"title": "Django Official Documentation", "url": "https://docs.djangoproject.com/", "type": "docs",
             "description": "Official Django docs with tutorials and comprehensive guides for building web apps.", "duration": "Ongoing reference"},
            {"title": "Django for Beginners", "url": "https://djangoforbeginners.com/", "type": "course",
             "description": "Step-by-step guide to building modern Django applications from scratch.", "duration": "15-20 hours"},
            {"title": "Django REST Framework", "url": "https://www.django-rest-framework.org/tutorial/quickstart/", "type": "tutorial",
             "description": "Essential for building APIs. Learn REST principles and DRF implementation.", "duration": "5-10 hours"}
        ],
        "javascript": [
            {"title": "MDN JavaScript Guide", "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide", "type": "tutorial",
             "description": "Mozilla's comprehensive JavaScript guide covering basics to advanced concepts.", "duration": "15-20 hours"},
            {"title": "JavaScript.info", "url": "https://javascript.info/", "type": "course",
             "description": "Modern JavaScript tutorial with detailed explanations and interactive examples.", "duration": "30-40 hours"},
            {"title": "Eloquent JavaScript", "url": "https://eloquentjavascript.net/", "type": "book",
             "description": "In-depth book on JavaScript programming with exercises and projects.", "duration": "25-35 hours"}
        ],
        "react": [
            {"title": "React Official Tutorial", "url": "https://react.dev/learn", "type": "tutorial",
             "description": "Official React tutorial with interactive exercises. Best place to start.", "duration": "3-5 hours"},
            {"title": "React Documentation", "url": "https://react.dev/", "type": "docs",
             "description": "Comprehensive React docs with examples, API reference and best practices.", "duration": "Ongoing reference"},
            {"title": "Full Stack Open - React", "url": "https://fullstackopen.com/en/", "type": "course",
             "description": "University-level full stack course with deep dive into React and modern web development.", "duration": "40-50 hours"}
        ],
        "sql": [
            {"title": "SQLZoo Interactive", "url": "https://sqlzoo.net/", "type": "tutorial",
             "description": "Interactive SQL tutorials with instant feedback. Practice queries in your browser.", "duration": "8-12 hours"},
            {"title": "W3Schools SQL Tutorial", "url": "https://www.w3schools.com/sql/", "type": "tutorial",
             "description": "Quick reference and basic tutorials for SQL syntax and operations.", "duration": "5-8 hours"},
            {"title": "Mode SQL Analytics", "url": "https://mode.com/sql-tutorial/", "type": "course",
             "description": "SQL for data analysis. Learn queries, joins, aggregations and window functions.", "duration": "10-15 hours"}
        ],
        "docker": [
            {"title": "Docker Getting Started", "url": "https://docs.docker.com/get-started/", "type": "tutorial",
             "description": "Official Docker tutorial covering containers, images, and basic orchestration.", "duration": "4-6 hours"},
            {"title": "Docker Documentation", "url": "https://docs.docker.com/", "type": "docs",
             "description": "Complete Docker reference with guides for containerization and deployment.", "duration": "Ongoing reference"},
            {"title": "Docker for Developers", "url": "https://docker-curriculum.com/", "type": "course",
             "description": "Practical Docker tutorial for developers. Build, ship, and run applications.", "duration": "6-8 hours"}
        ],
        "aws": [
            {"title": "AWS Free Training", "url": "https://aws.amazon.com/training/", "type": "course",
             "description": "Official AWS training including free digital courses and hands-on labs.", "duration": "10-40 hours"},
            {"title": "AWS Solutions Architect", "url": "https://aws.amazon.com/certification/certified-solutions-architect-associate/", "type": "certification",
             "description": "Industry-recognized certification. Great for learning AWS architecture.", "duration": "40-60 hours"},
            {"title": "AWS Documentation", "url": "https://docs.aws.amazon.com/", "type": "docs",
             "description": "Comprehensive AWS service documentation with tutorials and best practices.", "duration": "Ongoing reference"}
        ],
        "node.js": [
            {"title": "Node.js Official Docs", "url": "https://nodejs.org/en/learn/getting-started/introduction-to-nodejs", "type": "docs",
             "description": "Official Node.js documentation with guides on async programming and modules.", "duration": "Ongoing reference"},
            {"title": "The Odin Project - Node", "url": "https://www.theodinproject.com/paths/full-stack-javascript/courses/nodejs", "type": "course",
             "description": "Full Node.js course covering Express, databases, and production deployment.", "duration": "30-40 hours"},
            {"title": "Node.js Best Practices", "url": "https://github.com/goldbergyoni/nodebestpractices", "type": "guide",
             "description": "Comprehensive guide to Node.js best practices covering 80+ topics.", "duration": "5-10 hours"}
        ],
        "git": [
            {"title": "Git Official Book", "url": "https://git-scm.com/book/en/v2", "type": "book",
             "description": "Pro Git book - comprehensive guide from basics to advanced Git workflows.", "duration": "15-20 hours"},
            {"title": "GitHub Learning Lab", "url": "https://github.com/apps/github-learning-lab", "type": "tutorial",
             "description": "Interactive Git and GitHub tutorials with real repositories.", "duration": "5-8 hours"},
            {"title": "Atlassian Git Tutorial", "url": "https://www.atlassian.com/git/tutorials", "type": "tutorial",
             "description": "Clear explanations of Git concepts with visual diagrams.", "duration": "8-12 hours"}
        ]
    }
    
    resources = []
    for skill in cleaned_skills[:10]:  # Limit to 10 skills
        skill_lower = skill.lower()
        if skill_lower in resource_map:
            resources.append({
                "skill": skill,
                "resources": resource_map[skill_lower]
            })
        else:
            # Enhanced generic resources for unknown skills
            resources.append({
                "skill": skill,
                "resources": [
                    {
                        "title": f"{skill.title()} Tutorial on YouTube",
                        "url": f"https://www.youtube.com/results?search_query={skill}+tutorial+2024",
                        "type": "video",
                        "description": f"Video tutorials and courses on {skill}. Filter by view count and recent uploads.",
                        "duration": "Varies"
                    },
                    {
                        "title": f"{skill.title()} on Udemy",
                        "url": f"https://www.udemy.com/courses/search/?q={skill}",
                        "type": "course",
                        "description": f"Professional courses on {skill}. Look for high ratings and recent updates.",
                        "duration": "10-30 hours"
                    },
                    {
                        "title": f"{skill.title()} Documentation",
                        "url": f"https://www.google.com/search?q={skill}+official+documentation",
                        "type": "docs",
                        "description": f"Official documentation and guides for {skill}. Always the most accurate source.",
                        "duration": "Ongoing reference"
                    }
                ]
            })
    
    return resources

def get_learning_resources_with_gemini(missing_skills: List[str]) -> List[Dict]:
    """Get learning resources for missing skills."""
    if not isinstance(missing_skills, list):
        raise ValidationError("Missing skills must be provided as a list")

    cleaned_skills = [s.lower().strip() for s in missing_skills if s]
    if not cleaned_skills:
        return []

    try:
        prompt = (
            "For these missing skills, list up to three high-quality learning resources per skill. "
            "Return ONLY valid JSON array with items containing: "
            "skill (string) and resources (array of {title, url, type}).\n\n"
            f"Missing Skills: {cleaned_skills}"
        )

        response = generate_with_retry(
            prompt,
            temperature=0.2,
            max_tokens=300
        )
        return json.loads(response.text.strip())
    except Exception as e:
        # Fallback to basic resources
        logger.warning(f"AI learning resources failed: {str(e)}")
        logger.info("Using fallback learning resources...")
        return get_basic_learning_resources(cleaned_skills)
    

def extract_text_from_file(file_path: str) -> str:
    """
    Extract text from PDF, DOCX, DOC, or TXT files with multiple fallback strategies.
    Uses multiple libraries and OCR for maximum extraction success.
    """
    # Handle file path or file object
    if hasattr(file_path, 'path'):
        # Django UploadedFile object
        file_path = file_path.path
    elif hasattr(file_path, 'name'):
        # File object without path attribute
        file_path = str(file_path)
    
    ext = os.path.splitext(file_path)[1][1:].lower()
    
    try:
        if ext == 'pdf':
            # Strategy 1: Try pdfminer (best for most PDFs)
            try:
                text = extract_text(file_path)
                if text and len(text.strip()) > 20:
                    logger.info(f"pdfminer extracted {len(text)} characters successfully")
            except Exception as pdfminer_error:
                logger.warning(f"pdfminer extraction failed: {pdfminer_error}")
                text = ""
            
            # Strategy 2: If pdfminer fails, try PyPDF2
            if not text.strip():
                try:
                    import PyPDF2
                    with open(file_path, 'rb') as pdf_file:
                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                        text = ''
                        for page in pdf_reader.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text += page_text + '\n'
                        if text.strip():
                            logger.info(f"PyPDF2 extracted {len(text)} characters successfully")
                except ImportError:
                    logger.error("PyPDF2 not installed. Install with: pip install PyPDF2")
                except Exception as pypdf_error:
                    logger.warning(f"PyPDF2 extraction failed: {pypdf_error}")
            
            # Strategy 3: If still no text, try OCR
            if not text.strip():
                # Check if Tesseract is available before attempting OCR
                tesseract_available = True
                try:
                    pytesseract.get_tesseract_version()
                except Exception:
                    tesseract_available = False
                
                if tesseract_available:
                    try:
                        # Fallback to OCR for scanned PDFs
                        logger.info("PDF has no selectable text, attempting OCR...")
                        pages = convert_from_path(file_path)
                        text = "\n".join([pytesseract.image_to_string(p) for p in pages])
                        logger.info("OCR extraction successful")
                    except Exception as ocr_error:
                        logger.error(f"OCR extraction failed: {ocr_error}")
                        raise ValidationError(
                            "PDF contains no readable text and OCR extraction failed. "
                            "Please provide a text-selectable PDF or convert to DOCX format."
                        )
                else:
                    logger.warning("Tesseract OCR is not installed, cannot extract from scanned PDFs")
                    raise ValidationError(
                        "PDF contains no readable text. "
                        "Please provide a text-selectable PDF or convert to DOCX format. "
                        "Note: OCR capability is not available on this system."
                    )
            
            if not text.strip():
                raise ValidationError("PDF contains no readable text. Please provide a selectable-text PDF or DOCX.")
            return text

        elif ext in ['docx', 'doc']:
            text = docx2txt.process(file_path)
            if not text.strip():
                raise ValidationError("Uploaded DOC/DOCX contains no readable text.")
            return text

        elif ext == 'txt':
            # Handle plain text files
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            if not text.strip():
                raise ValidationError("Uploaded TXT file contains no readable text.")
            return text

        else:
            raise ValidationError(f"Unsupported file type: {ext}")

    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(f"Failed to extract text: {str(e)}")
    

def parse_resume_file(file_path):
    text = extract_text_from_file(file_path) or ""
    
    # Check if text was extracted successfully
    if not text or len(text.strip()) < 20:
        raise ValidationError("Could not extract sufficient text from the resume file. Please ensure the file is not corrupted or password-protected.")

    prompt = f"""
    You are an AI resume parser. Extract the following fields from the resume:
    - name: The person's full name (ONLY human names, NOT departments/majors/colleges)
    - email: Email address
    - phone: Phone number
    - education: Educational qualifications as a list (include degree, institution, year)
    - experience: Work experience as a list (include company, role, duration). DO NOT include education dates or course durations.
    - skills: Technical and job-relevant skills only (NOT soft skills or generic phrases)
    - parsed_text: Raw cleaned text

    CRITICAL RULES for "name" field:
    - Extract ONLY the person's actual name (e.g., "John Doe", "Habib Parvej", "Sarah Smith")
    - DO NOT extract: university names, college names, department names (like "Computer Science", "CSE", "ECE")
    - DO NOT extract: job titles, company names, degrees (like "B.Tech", "M.Tech")
    - DO NOT extract: headings like "Resume", "CV", "Curriculum Vitae"
    - The name should be 2-4 words maximum and look like a human name
    - If you cannot find a clear person name, leave it empty

    CRITICAL RULES for "experience" field:
    - ONLY extract actual work experience (job roles at companies)
    - DO NOT extract education duration/course duration (e.g., "2020-2023" from college)
    - Each entry should have: Job Title + Company Name + Duration
    - Example: "Software Engineer at Google, 2022-2024"
    - If no work experience found, return empty list []

    Return the response as valid JSON like this:
    {{
      "name": "John Doe",
      "email": "john@example.com",
      "phone": "+1234567890",
      "education": ["B.Tech in Computer Science, XYZ University, 2020-2024"],
      "experience": ["Software Engineer at ABC Corp, 2024-Present"],
      "skills": ["Python", "Django", "SQL"],
      "parsed_text": "..."
    }}

    Resume:
    {text}
    """

    try:
        response = generate_with_retry(
            prompt,
            temperature=0.0,
            max_tokens=1024
        )
        
        response_text = response.text.strip()

        # Remove code fences if present
        match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", response_text)
        cleaned = match.group(1) if match else response_text

        try:
            parsed = json.loads(cleaned) if cleaned else {}
        except json.JSONDecodeError:
            # Attempt to repair invalid JSON
            repaired = cleaned.strip()
            repaired = repaired.replace("\n", " ").replace("\r", " ")
            repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
            try:
                parsed = json.loads(repaired)
            except Exception:
                parsed = {}

        # Enrich and fill missing defaults
        parsed = parsed or {}
        parsed = enrich_parsed_resume(parsed, fallback_text=text)

        # Ensure parsed_text always exists
        if "parsed_text" not in parsed or not parsed["parsed_text"]:
            parsed["parsed_text"] = text[:2000]

        # Ensure all required fields are present (AI might have failed due to quota)
        parsed.setdefault("name", "")
        parsed.setdefault("email", "")
        parsed.setdefault("phone", "")
        parsed.setdefault("skills", [])
        parsed.setdefault("education", [])
        parsed.setdefault("experience", [])
        
        # If critical fields are still empty after enrichment, force fallback extraction
        if not parsed.get("name") or not parsed.get("email"):
            logger.warning("Critical fields empty after AI parsing, forcing comprehensive fallback extraction...")
            parsed = enrich_parsed_resume(parsed, fallback_text=text, force_extraction=True)

        return parsed

    except Exception as e:
        # If AI parsing completely fails (e.g., API quota exceeded), fallback to regex-based extraction
        error_msg = str(e).lower()
        if "quota" in error_msg or "429" in error_msg or "rate" in error_msg:
            logger.warning(f"API quota exceeded or rate limit hit: {str(e)}")
            logger.info("Using comprehensive fallback regex extraction due to API limits...")
        else:
            logger.warning(f"AI parsing failed: {str(e)}")
            logger.info("Using fallback regex extraction...")
        
        # Create empty structure and enrich it with forced extraction
        parsed = {
            "parsed_text": text[:2000] if text else "",
            "name": "",
            "email": "",
            "phone": "",
            "skills": [],
            "education": [],
            "experience": []
        }
        parsed = enrich_parsed_resume(parsed, fallback_text=text, force_extraction=True)
        
        return parsed


def enrich_parsed_resume(data: dict, fallback_text: str = "", force_extraction: bool = False) -> dict:
    """
    Enrich parsed resume data with fallback regex extraction
    
    Args:
        data: Parsed resume data dictionary
        fallback_text: Full resume text to extract from
        force_extraction: If True, always perform extraction even if fields are populated
    """
    # ALWAYS use fallback_text if provided (full text), otherwise use truncated parsed_text
    text = fallback_text or data.get("parsed_text", "") or ""
    
    # Ensure parsed_text is always populated
    if not data.get("parsed_text"):
        data["parsed_text"] = text

    # Extract email with multiple strategies
    if not data.get("email") or force_extraction:
        # Strategy 1: Find email after explicit label (highest confidence)
        label_patterns = [
            r"(?:email|e-mail|mail|contact)[\s:]+([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
            r"(?:^|\n)(?:email|e-mail)[\s:]*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})"
        ]
        
        email_found = False
        for pattern in label_patterns:
            label_match = re.search(pattern, text, re.I | re.M)
            if label_match:
                email_candidate = label_match.group(1).lower().strip()
                # Validate email format more strictly
                if re.match(r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$", email_candidate):
                    data["email"] = email_candidate
                    email_found = True
                    break
        
        # Strategy 2: Find any email in first 1000 characters (contact area)
        if not email_found:
            top_section = text[:1000]
            email_matches = re.findall(r"\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b", top_section, re.I)
            if email_matches:
                # Take the first valid email
                for email in email_matches:
                    email = email.lower().strip()
                    if re.match(r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$", email):
                        data["email"] = email
                        email_found = True
                        break
        
        # Strategy 3: Search entire document as last resort
        if not email_found:
            match = re.search(r"\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b", text)
            if match:
                email = match.group(1).lower().strip()
                if re.match(r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$", email):
                    data["email"] = email
                else:
                    data["email"] = ""
            else:
                data["email"] = ""
        
        if not data.get("email"):
            data["email"] = ""

    # Extract phone with improved pattern (handles various formats)
    if not data.get("phone") or force_extraction:
        # First, explicitly check and skip roll numbers, student IDs, registration numbers
        # These should NEVER be extracted as phone numbers
        roll_patterns = [
            r"(?:roll|reg|id|regno|student|enrollment|admission|registration)[\s_]*(?:no|number|num|#)?[\s:_-]+(\d+)",
        ]
        roll_numbers = set()
        for pattern in roll_patterns:
            matches = re.findall(pattern, text, re.I)
            roll_numbers.update(matches)
        
        logger.info(f"Found {len(roll_numbers)} roll/ID numbers to exclude: {list(roll_numbers)[:3]}")
        
        # Now check for phone/mobile/contact labels (positive indicators)
        label_patterns = [
            r"(?:phone|mobile|contact|cell|tel|telephone|whatsapp)[\s:]+([+]?[\d\s\-\(\)]+)",
            r"(?:^|\n)(?:phone|mobile|contact)[\s:]*(\+?[\d\s\-\(\)]+)"
        ]
        
        phone_found = False
        for pattern in label_patterns:
            match = re.search(pattern, text, re.I | re.M)
            if match:
                phone_candidate = match.group(1).strip()
                # Validate it looks like a phone number (has at least 10 digits)
                digits = re.findall(r'\d', phone_candidate)
                digits_only = ''.join(digits)
                
                # Skip if it's in our roll numbers set
                if digits_only in roll_numbers or digits_only[:8] in roll_numbers:
                    logger.debug(f"Skipping {phone_candidate} - matches roll number")
                    continue
                
                # Must have 10-15 digits to be valid
                if len(digits) >= 10 and len(digits) <= 15:
                    data["phone"] = phone_candidate
                    phone_found = True
                    logger.info(f"Phone found with label: {phone_candidate}")
                    break
        
        # If no labeled phone found, try multiple phone patterns
        # BUT be very careful not to pick up roll numbers
        if not phone_found:
            phone_patterns = [
                r"\+91[\s-]?\d{5}[\s-]?\d{5}",  # +91 82191-19441 (Indian format) - country code is strong indicator
                r"\+\d{1,3}[\s-]?\(?\d{3,5}\)?[\s-]?\d{3,5}[\s-]?\d{4}",  # International format with country code
                r"\d{5}[\s-]\d{5}",  # 82191-19441 (hyphenated 10-digit)
                r"\d{3}[-.\s]\d{3}[-.\s]\d{4}",  # 555-555-5555 (formatted with separators)
            ]
            for pattern in phone_patterns:
                match = re.search(pattern, text)
                if match:
                    phone_candidate = match.group(0).strip()
                    digits_only = re.sub(r'\D', '', phone_candidate)
                    
                    # Skip if it's a known roll number
                    if digits_only in roll_numbers:
                        continue
                    
                    # For patterns without country code, check nearby context more carefully
                    # Get 50 chars before the match to check context
                    match_pos = text.find(phone_candidate)
                    if match_pos > 0:
                        context_before = text[max(0, match_pos - 50):match_pos].lower()
                        # Skip if preceded by roll/id/registration keywords
                        if re.search(r'(?:roll|reg|id|regno|student|enrollment|admission)[\s_]*(?:no|number|num|#)?[\s:_-]*$', context_before):
                            continue
                    
                    # Additional validation for 10-digit numbers without formatting
                    # Only accept 10-digit numbers if they have good separators or country code
                    if len(digits_only) == 10 and not re.search(r'[-\.\s]', phone_candidate):
                        # Plain 10 digits with no separators - might be roll number
                        # Only accept if it's at the top of resume (contact info area)
                        lines_before = text[:match_pos].count('\n')
                        if lines_before > 10:  # Not in first ~10 lines
                            continue
                    
                    if 10 <= len(digits_only) <= 15:
                        data["phone"] = phone_candidate
                        phone_found = True
                        break
        
        if not data.get("phone"):
            data["phone"] = ""

    # Extract name - Multi-strategy approach with strict validation
    if not data.get("name") or force_extraction:
        # Define comprehensive exclusion keywords
        INSTITUTION_KEYWORDS = {
            'university', 'college', 'institute', 'school', 'academy', 'polytechnic',
            'iit', 'nit', 'iiit', 'bits', 'vidyalaya', 'vidyapeeth', 'vishwavidyalaya'
        }
        
        DEPARTMENT_KEYWORDS = {
            'computer science', 'information technology', 'mechanical engineering',
            'electrical engineering', 'electronics', 'civil engineering', 'chemical',
            'biotechnology', 'mathematics', 'physics', 'chemistry', 'business',
            'commerce', 'arts', 'science', 'engineering', 'technology', 'management',
            'cse', 'ece', 'eee', 'mech', 'it', 'cs', 'dept', 'department',
            'stream', 'branch', 'specialization', 'field'
        }
        
        DEGREE_KEYWORDS = {
            'bachelor', 'master', 'b.tech', 'm.tech', 'bca', 'mca', 'mba',
            'b.sc', 'm.sc', 'b.e', 'm.e', 'phd', 'diploma', 'btech', 'mtech',
            'degree', 'graduate', 'postgraduate', 'undergraduate'
        }
        
        JOB_TITLE_KEYWORDS = {
            'engineer', 'developer', 'manager', 'analyst', 'designer', 'consultant',
            'specialist', 'coordinator', 'lead', 'senior', 'junior', 'intern',
            'architect', 'administrator', 'officer', 'executive', 'associate',
            'assistant', 'trainee', 'supervisor', 'director', 'head'
        }
        
        # Strategy 1: Find name after explicit label (highest confidence)
        name_label_patterns = [
            r"(?:^|\n)(?:name|full name|candidate name)[\s:]+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,3})(?=\s*[\n\r]|$)",
            r"^([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\s*$"
        ]
        
        name_found = False
        for pattern in name_label_patterns:
            label_match = re.search(pattern, text, re.I | re.M)
            if label_match:
                name_candidate = label_match.group(1).strip()
                name_lower = name_candidate.lower()
                
                # Comprehensive validation
                is_valid = (
                    2 <= len(name_candidate.split()) <= 4 and  # 2-4 words
                    not any(keyword in name_lower for keyword in INSTITUTION_KEYWORDS) and
                    not any(keyword in name_lower for keyword in DEPARTMENT_KEYWORDS) and
                    not any(keyword in name_lower for keyword in DEGREE_KEYWORDS) and
                    not any(keyword in name_lower for keyword in JOB_TITLE_KEYWORDS) and
                    not re.search(r'\d', name_candidate) and  # No numbers
                    not re.search(r'[<>{}\[\]\\\\/@#$%^&*:]', name_candidate)  # No special chars
                )
                
                if is_valid:
                    data["name"] = name_candidate
                    name_found = True
                    break
        
        # Strategy 2: Balanced approach - Look for name in first 10 lines with proper filtering
        if not name_found:
            logger.info(f"Name not found via labels, checking first 10 lines...")
            for i, line in enumerate(text.splitlines()[:10]):
                line = line.strip()
                logger.debug(f"Line {i}: '{line}'")
                
                # Skip empty or very short lines
                if not line or len(line) < 3:
                    continue
                
                # Skip lines with clear non-name markers
                if '@' in line or 'http' in line or 'www.' in line or '+' in line[:5]:
                    continue
                
                # Skip pure section headers
                if line.lower() in ['resume', 'cv', 'curriculum vitae', 'objective', 'profile', 'summary', 
                                     'experience', 'education', 'skills', 'contact', 'projects', 'personal details']:
                    continue
                
                # Get words
                words = line.split()
                if len(words) < 2 or len(words) > 5:  # Names are typically 2-4 words
                    continue
                
                line_lower = line.lower()
                
                # Skip if contains common exclusion keywords
                if any(keyword in line_lower for keyword in ['university', 'college', 'institute', 'engineering',
                                                              'computer', 'science', 'technology', 'bachelor', 'master']):
                    continue
                
                # If first 3 lines, check for name patterns
                if i < 3:
                    # Must have proper capitalization (Title Case or ALL CAPS)
                    is_title_case = all(w[0].isupper() for w in words if w and len(w) > 1)
                    is_all_caps = line.isupper()
                    
                    if (is_title_case or is_all_caps) and 2 <= len(words) <= 4:
                        # Additional validation: no numbers, limited special chars
                        if not re.search(r'\d', line) and not re.search(r'[<>{}\[\]\\/@#$%^&*:]', line):
                            data["name"] = line.title() if is_all_caps else line
                            name_found = True
                            logger.info(f"Name found in first 3 lines: {data['name']}")
                            break
                
                line_lower = line.lower()
                
                # Skip only very obvious section headers
                if line_lower in ['work experience', 'professional experience', 'personal information',
                                  'technical skills', 'professional summary', 'career objective']:
                    continue
                
                # Pattern 1: Title Case - "John Doe" or "Sarah Smith"
                if re.match(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+$', line):
                    data["name"] = line
                    name_found = True
                    break
                
                # Pattern 2: All Caps - "JOHN DOE" (convert to title case)
                if line.isupper() and len(words) >= 1 and len(words) <= 4:
                    # Skip if it looks like a title
                    if not any(title in line_lower for title in ['engineer', 'developer', 'manager', 'analyst', 'designer']):
                        data["name"] = line.title()
                        name_found = True
                        break
                
                # Pattern 3: Single capitalized word (might be first name)
                if i < 5 and len(words) == 1 and words[0][0].isupper() and len(words[0]) > 2:
                    # Check if next line might be last name
                    lines = text.splitlines()
                    if i+1 < len(lines):
                        next_line = lines[i+1].strip()
                        next_words = next_line.split()
                        if next_words and next_words[0][0].isupper() and len(next_words[0]) > 2:
                            # Combine first and last name
                            data["name"] = f"{words[0]} {next_words[0]}"
                            name_found = True
                            break
                
                # Pattern 4: Mixed case with at least 2 capitalized words
                if i < 8 and len(words) >= 2:
                    capitalized_words = [w for w in words if w and len(w) > 1 and w[0].isupper()]
                    if len(capitalized_words) >= 2:
                        data["name"] = ' '.join(capitalized_words)
                        name_found = True
                        logger.info(f"Name found (Pattern 4 - capitalized words): {data['name']}")
                        break
                
                # Pattern 5: First non-empty line as last resort (first 2 lines only)
                if i < 2 and len(words) >= 1 and len(words) <= 4:
                    # Must have at least one capital letter
                    if any(c.isupper() for c in line):
                        data["name"] = line
                        name_found = True
                        logger.info(f"Name found (Pattern 5 - first line): {data['name']}")
                        break
        
        if not name_found:
            logger.warning("Name extraction failed - no valid pattern found in first 15 lines")
            data["name"] = ""
    
    # Legacy fallback (kept for compatibility, but should not execute if above works)
    if not data.get("name"):
        first_line = ""
        for line in text.splitlines()[:10]:  # Reduced to first 10 lines only
            line = line.strip()
            
            # Skip empty lines
            if not line or len(line) < 3:
                continue
            
            # Skip lines with contact info
            if "@" in line or "http" in line.lower():
                continue
            
            # Skip pure numbers or lines with mostly numbers
            if re.match(r"^[\d\s\-\+\(\)]+$", line):
                continue
            
            # Skip lines that look like IDs, roll numbers, or registration numbers
            if re.search(r'(?:roll|reg|id|regno|student|enrollment)[\s_]*(?:no|number|#)?[\s:]+', line, re.I):
                continue
            
            # Skip common headers/sections
            if any(keyword in line.lower() for keyword in [
                'resume', 'curriculum vitae', 'cv', 'objective', 'profile',
                'summary', 'experience', 'education', 'skills', 'projects',
                'certifications', 'achievements', 'references', 'contact',
                'personal details', 'professional', 'career', 'assignment',
                'subject', 'topic', 'semester', 'year'
            ]):
                continue
            
            # Skip lines with "university", "college", "institute", "school"
            if any(keyword in line.lower() for keyword in [
                'university', 'college', 'institute', 'school', 'academy',
                'iit', 'nit', 'iiit', 'bits', 'polytechnic', 'vidyalaya', 'dept'
            ]):
                continue
            
            # Skip department/major names (very common issue)
            if any(keyword in line.lower() for keyword in [
                'computer science', 'information technology', 'mechanical engineering',
                'electrical engineering', 'electronics', 'civil engineering',
                'chemical engineering', 'biotechnology', 'mathematics',
                'physics', 'chemistry', 'business administration', 'commerce',
                'arts', 'science', 'engineering', 'technology', 'management',
                'cse', 'ece', 'eee', 'mech', 'it dept', 'dept', 'department',
                'bachelor', 'master', 'b.tech', 'm.tech', 'bca', 'mca', 'mba',
                'b.sc', 'm.sc', 'b.e', 'm.e', 'phd', 'diploma', 'btech', 'mtech'
            ]):
                continue
            
            # Skip lines with common job titles or professional designations
            if any(keyword in line.lower() for keyword in [
                'engineer', 'developer', 'manager', 'analyst', 'designer',
                'consultant', 'specialist', 'coordinator', 'lead', 'senior',
                'junior', 'intern', 'architect', 'administrator', 'officer'
            ]):
                continue
            
            # Skip common company names and tech companies
            if any(keyword in line.lower() for keyword in [
                'microsoft', 'google', 'amazon', 'facebook', 'meta', 'apple',
                'ibm', 'oracle', 'infosys', 'tcs', 'wipro', 'cognizant',
                'accenture', 'deloitte', 'pwc', 'kpmg', 'ey', 'capgemini',
                'tech', 'systems', 'solutions', 'services', 'corp', 'inc',
                'ltd', 'pvt', 'limited', 'corporation', 'company'
            ]):
                continue
            
            # Name should be 1-5 words typically (allow 5 for middle names)
            words = line.split()
            if len(words) > 6 or len(words) == 0:
                continue
            
            # Skip if it contains special characters that don't belong in names
            if re.search(r'[<>{}[\]\\\/|~`@#$%^&*:]', line):  # Added colon to skip "Location:", etc.
                continue
            
            # Skip lines that are all caps (usually headings) - unless it's short (2-3 words)
            # But allow all-caps names if they're 2-3 words and at the very top
            is_all_caps = line.isupper()
            is_short = len(words) <= 3
            if is_all_caps and (not is_short or len(line) > 25):
                continue
            
            # Additional check: skip if it looks like a degree or qualification
            if re.search(r'\b(b\.|m\.|ph\.?d|degree|diploma)\b', line.lower()):
                continue
            
            # Skip lines with numbers (likely not a name)
            if re.search(r'\d', line):
                continue
            
            # Check if it looks like a proper name (starts with capital letters)
            # Most names have multiple words starting with capital letters
            # Allow all-caps if it's 2-3 words (common in resumes)
            if re.match(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+$', line):
                # Perfect match: Title Case name
                first_line = line
                break
            elif is_all_caps and is_short and re.match(r'^[A-Z\s]+$', line):
                # All caps, 2-3 words - likely a name at top of resume
                first_line = line.title()  # Convert to Title Case
                break
            
            # Fallback: accept any line with 2-4 title-case words
            if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if w):
                first_line = line
                break
        
        data["name"] = first_line

    # Extract education
    if (not data.get("education") or len(data.get("education", [])) == 0) or force_extraction:
        edu_matches = re.findall(
            r"(Bachelor|Master|B\.?Tech|M\.?Tech|MCA|BCA|BSc|MSc|MBA|PhD|Diploma).*",
            text,
            re.I
        )
        # Clean and deduplicate
        edu_list = []
        for match in edu_matches:
            cleaned = match.strip()
            if cleaned and len(cleaned) > 5:  # Meaningful education entries
                edu_list.append(cleaned[:100])  # Limit length
        data["education"] = list(set(edu_list)) if edu_list else []

    # Extract skills
    if (not data.get("skills") or len(data.get("skills", [])) == 0) or force_extraction:
        data["skills"] = extract_skills_from_text(text)
    
    # Extract experience sections (basic)
    if (not data.get("experience") or len(data.get("experience", [])) == 0) or force_extraction:
        # Only look for actual job experience with company/role context
        # DO NOT extract standalone year ranges (those are usually education dates)
        exp_patterns = [
            r"((?:Software Engineer|Developer|Manager|Analyst|Designer|Consultant|Engineer|Specialist|Lead|Architect).*?(?:at|@|,)\s+[A-Z]\w+.*?(?:\d{4}\s*[-–]\s*(?:\d{4}|Present|Current))?)",
        ]
        exp_matches = []
        
        # Education-related keywords to filter out
        education_keywords = [
            'university', 'college', 'institute', 'school', 'academy',
            'bachelor', 'master', 'b.tech', 'm.tech', 'bca', 'mca', 'mba',
            'degree', 'diploma', 'phd', 'bsc', 'msc', 'graduation',
            'undergraduate', 'postgraduate', 'course', 'semester', 'cgpa', 'gpa'
        ]
        
        for pattern in exp_patterns:
            matches = re.findall(pattern, text, re.I)
            exp_matches.extend(matches)
        
        # Clean and filter out education-related entries
        exp_list = []
        for match in exp_matches[:10]:  # Limit to 10 experience entries
            cleaned = match.strip()
            cleaned_lower = cleaned.lower()
            
            # Skip if it contains education keywords
            if any(edu_keyword in cleaned_lower for edu_keyword in education_keywords):
                continue
            
            # Skip if it's just a year range without role/company context
            if re.match(r'^\d{4}\s*[-–]\s*(?:\d{4}|present|current)\s*$', cleaned_lower.strip()):
                continue
            
            # Must have meaningful content (role + company)
            if cleaned and len(cleaned) > 15:
                exp_list.append(cleaned[:200])  # Limit length
        
        data["experience"] = list(set(exp_list)) if exp_list else []

    return data


def extract_skills_from_text(text: str) -> List[str]:
    """Extract skills from text using NLP and pattern matching."""
    if not text:
        return []
    
    skills = set()
    
    # Common stopwords to exclude (non-skill words)
    stopwords = {
        'we', 'are', 'looking', 'for', 'the', 'a', 'an', 'and', 'or', 'but',
        'in', 'on', 'at', 'to', 'from', 'with', 'required', 'skills', 'preferred',
        'experience', 'expertise', 'knowledge', 'understanding', 'ability',
        'responsibilities', 'requirements', 'qualifications', 'education',
        'degree', 'bachelor', 'master', 'years', 'year', 'company', 'team',
        'work', 'working', 'job', 'position', 'role', 'candidate', 'candidates',
        'must', 'should', 'will', 'can', 'may', 'have', 'has', 'been', 'is', 'was',
        'areas', 'area', 'powered', 'friendly', 'content', 'generation', 'resume',
        'applications', 'learning', 'analysis', 'patterns', 'operations'
    }
    
    # Phrases to exclude (noise from resumes)
    exclude_phrases = {
        'high-risk', 'high risk', 'ai-powered', 'ats-friendly', 'job-fit',
        'content generation', 'data analysis', 'key patterns', 'continuous learning'
    }
    
    try:
        # Try spaCy first
        doc = NLP(text.lower())
        
        # Comprehensive skill patterns - ONLY technical skills
        patterns = [
            # Programming languages
            r'\b(python|java|javascript|typescript|c\+\+|c#|ruby|php|swift|kotlin|scala|rust|go|perl|r|matlab)\b',
            # Web frameworks
            r'\b(react|angular|vue|node\.?js|django|flask|spring|express|laravel|rails|asp\.net|fastapi)\b',
            # Databases
            r'\b(sql|mysql|postgresql|mongodb|oracle|redis|cassandra|dynamodb|sqlite|mariadb|firestore)\b',
            # Cloud & DevOps
            r'\b(aws|azure|gcp|docker|kubernetes|jenkins|terraform|ansible|ci/cd|devops)\b',
            # Tools & Technologies
            r'\b(git|github|gitlab|bitbucket|jira|confluence|slack|tableau|power bi|excel|linux|unix|windows)\b',
            # Web Technologies
            r'\b(html|css|sass|less|bootstrap|tailwind|jquery|ajax|rest|restful|api|graphql|json|xml)\b',
            # Data Science & ML (use full phrases to avoid picking up random "learning")
            r'\b(machine learning|deep learning|tensorflow|pytorch|scikit-learn|pandas|numpy|keras|opencv)\b',
            # Methodologies
            r'\b(agile|scrum|kanban|waterfall|tdd|bdd|microservices)\b',
            # Other technical skills
            r'\b(elasticsearch|kafka|rabbitmq|nginx|apache|tomcat|maven|gradle|npm|webpack|babel)\b'
        ]
        
        # Pattern matching - these are definite technical skills
        for pattern in patterns:
            matches = re.findall(pattern, text.lower())
            skills.update(matches)
        
        # Filter out stopwords, names, and noise
        # Remove any skill that looks like a person's name or contains excluded phrases
        filtered_skills = set()
        for skill in skills:
            skill_lower = skill.lower()
            # Skip if it's in exclude list
            if any(excluded in skill_lower for excluded in exclude_phrases):
                continue
            # Skip if it contains numbers followed by "risk" or other noise words
            if re.search(r'\d+\+?\s*(risk|area|pattern)', skill_lower):
                continue
            # Skip if it looks like a person's name (title case with multiple words)
            words = skill.split()
            if len(words) >= 2 and all(w.istitle() or w[0].isupper() for w in words if w):
                continue
            # Skip if it's too long (likely a phrase, not a skill)
            if len(skill) > 25:
                continue
            
            filtered_skills.add(skill)
        
        return sorted(filtered_skills)[:30]  # Return up to 30 unique technical skills
        
    except Exception as e:
        # Fallback to pattern-only matching if spaCy fails
        logger.warning(f"spaCy processing failed, using pattern matching only: {e}")
        
        patterns = [
            r'\b(python|java|javascript|react|angular|vue|node\.?js|django|flask|spring)\b',
            r'\b(sql|mongodb|postgresql|mysql|aws|azure|gcp|docker|kubernetes|git|jenkins)\b',
            r'\b(agile|scrum|html|css|bootstrap|jquery|ajax|rest|api|json|xml|soap|graphql)\b',
            r'\b(machine learning|deep learning|tensorflow|pytorch|scikit-learn|pandas|numpy)\b',
            r'\b(c\+\+|c#|ruby|php|swift|kotlin|typescript|scala|rust|go|perl)\b',
            r'\b(excel|powerpoint|word|tableau|power bi|sap|salesforce|jira|confluence)\b'
        ]
        
        for pattern in patterns:
            skills.update(re.findall(pattern, text.lower()))
        
        return sorted(skills)[:30]

def optimize_resume_for_ats(resume_text: str, job_description: str = "") -> str:
    """Optimize resume text for Applicant Tracking Systems."""
    try:
        if not resume_text:
            return ""
            
        if not job_description:
            return resume_text
            
        job_keywords = extract_skills_from_text(job_description)
        resume_skills = extract_skills_from_text(resume_text)
        missing_keywords = [kw for kw in job_keywords if kw not in resume_skills]
        
        if missing_keywords:
            return f"{resume_text}\n\nAdditional Skills: {', '.join(missing_keywords[:5])}"
        return resume_text
    except Exception as e:
        raise ValidationError(f"Failed to optimize resume: {str(e)}")

def calculate_user_readiness_score(user_profile) -> float:
    """Calculate a readiness score based on user's job search activity."""
    try:
        score = 20.0  # Base score
        
        # Applications submitted
        score += min(user_profile.total_applications * 2, 20)
        
        # Interviews attended
        score += min(user_profile.interviews_attended * 5, 30)
        
        # Offers received
        score += min(user_profile.offers_received * 10, 30)
        
        return min(score, 100.0)
    except Exception as e:
        raise ValidationError(f"Failed to calculate readiness score: {str(e)}")


def calculate_ats_score(resume_text: str, skills: List[str]) -> Dict:
    """
    Calculate ATS (Applicant Tracking System) score and provide improvement suggestions
    
    Returns:
        {
            "ats_score": 0-100,
            "strengths": [...],
            "weaknesses": [...],
            "suggestions": [...],
            "keyword_match": 0-100,
            "format_score": 0-100,
            "content_score": 0-100
        }
    """
    try:
        prompt = f"""
You are an ATS (Applicant Tracking System) analyzer. Analyze this resume and provide a detailed ATS score.

Resume Text:
{resume_text[:2000]}

Extracted Skills:
{', '.join(skills[:20])}

Analyze and return JSON with:
- ats_score (0-100): Overall ATS compatibility score
- keyword_match (0-100): How well keywords are used
- format_score (0-100): Format and structure quality
- content_score (0-100): Content quality and relevance
- strengths (array of strings): What the resume does well (3-5 items)
- weaknesses (array of strings): What needs improvement (3-5 items)
- suggestions (array of strings): Specific actionable improvements (5-7 items)

Return ONLY valid JSON, no extra text.
"""
        
        response = generate_with_retry(
            prompt,
            temperature=0.2,
            max_tokens=800
        )
        
        raw = response.text.strip()
        
        # Remove code fences
        if raw.startswith("```") and raw.endswith("```"):
            lines = raw.splitlines()
            raw = "\n".join(lines[1:-1]).strip()
        
        result = json.loads(raw)
        
        # Ensure all required fields exist
        return {
            "ats_score": int(result.get("ats_score", 70)),
            "keyword_match": int(result.get("keyword_match", 70)),
            "format_score": int(result.get("format_score", 75)),
            "content_score": int(result.get("content_score", 70)),
            "strengths": result.get("strengths", []),
            "weaknesses": result.get("weaknesses", []),
            "suggestions": result.get("suggestions", [])
        }
        
    except Exception as e:
        # If AI fails, perform basic rule-based analysis
        logger.warning(f"AI-based ATS analysis failed, using rule-based fallback: {e}")
        return calculate_ats_score_fallback(resume_text, skills)


def calculate_ats_score_fallback(resume_text: str, skills: List[str]) -> Dict:
    """
    Fallback function to calculate ATS score using rule-based analysis
    when AI API is unavailable
    """
    resume_lower = resume_text.lower()
    
    # Calculate keyword match score
    keyword_score = 0
    skill_count = len(skills)
    if skill_count > 0:
        keyword_score = min(100, skill_count * 5)  # 5 points per skill, max 100
    
    # Calculate format score based on resume structure
    format_score = 60  # Base score
    format_checks = {
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "phone": r'\b\d{10}\b|\b\(\d{3}\)\s*\d{3}[-.\s]?\d{4}\b',
        "education": r'\b(education|degree|bachelor|master|phd|university|college)\b',
        "experience": r'\b(experience|work|employment|position|role)\b',
        "skills": r'\b(skills|technologies|tools|proficient)\b',
    }
    
    for key, pattern in format_checks.items():
        if re.search(pattern, resume_lower):
            format_score += 8
    
    # Calculate content score
    content_score = 50  # Base score
    word_count = len(resume_text.split())
    
    # Length check (optimal: 400-800 words)
    if 400 <= word_count <= 800:
        content_score += 20
    elif 200 <= word_count < 400 or 800 < word_count <= 1200:
        content_score += 10
    
    # Action verbs check
    action_verbs = ['developed', 'managed', 'created', 'led', 'designed', 'implemented', 
                    'achieved', 'improved', 'analyzed', 'coordinated', 'executed']
    action_count = sum(1 for verb in action_verbs if verb in resume_lower)
    content_score += min(20, action_count * 2)
    
    # Quantifiable achievements
    if re.search(r'\d+%|\$\d+|increased|decreased|improved|reduced', resume_lower):
        content_score += 10
    
    # Cap scores at 100
    keyword_score = min(100, keyword_score)
    format_score = min(100, format_score)
    content_score = min(100, content_score)
    
    # Calculate overall ATS score
    ats_score = int((keyword_score * 0.4) + (format_score * 0.3) + (content_score * 0.3))
    
    # Generate strengths
    strengths = []
    if skill_count >= 5:
        strengths.append(f"Strong skill set with {skill_count} identified skills")
    if re.search(format_checks['email'], resume_lower):
        strengths.append("Contact information clearly displayed")
    if action_count >= 3:
        strengths.append("Good use of action verbs to describe experience")
    if re.search(r'\d+%|\$\d+', resume_lower):
        strengths.append("Contains quantifiable achievements")
    if not strengths:
        strengths.append("Resume successfully parsed and analyzed")
    
    # Generate weaknesses
    weaknesses = []
    if skill_count < 3:
        weaknesses.append("Limited technical skills identified")
    if word_count < 200:
        weaknesses.append("Resume content is too brief")
    elif word_count > 1000:
        weaknesses.append("Resume may be too lengthy")
    if not re.search(format_checks['education'], resume_lower):
        weaknesses.append("Education section not clearly identified")
    if action_count < 2:
        weaknesses.append("Few action verbs used to describe experience")
    if not weaknesses:
        weaknesses.append("Consider adding more quantifiable achievements")
    
    # Generate suggestions
    suggestions = []
    if skill_count < 5:
        suggestions.append("Add more relevant technical skills to improve keyword matching")
    if not re.search(r'\d+%|\$\d+', resume_lower):
        suggestions.append("Include quantifiable achievements (e.g., 'Increased sales by 25%')")
    if action_count < 3:
        suggestions.append("Use more action verbs (e.g., 'Developed', 'Managed', 'Led')")
    suggestions.append("Ensure all sections are clearly labeled (Education, Experience, Skills)")
    suggestions.append("Use industry-standard keywords relevant to your target role")
    suggestions.append("Keep formatting simple and ATS-friendly (avoid tables, graphics)")
    suggestions.append("Include relevant certifications and professional development")
    
    return {
        "ats_score": ats_score,
        "keyword_match": keyword_score,
        "format_score": format_score,
        "content_score": content_score,
        "strengths": strengths[:5],
        "weaknesses": weaknesses[:5],
        "suggestions": suggestions[:7]
    }