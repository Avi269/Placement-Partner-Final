import re
import json
import os
from typing import Dict, List, Tuple, Optional
import spacy
from pyresparser import ResumeParser
import docx2txt
from pdf2image import convert_from_path
import pytesseract
from pdfminer.high_level import extract_text
from django.conf import settings
from django.core.exceptions import ValidationError, ImproperlyConfigured
from time import sleep

# Import model backends
try:
    from .model_backends import get_model, MODEL_MANAGER
    MODEL = get_model()
    print(f"✓ Using AI model backend: {MODEL.get_backend_name()}")
except Exception as e:
    print(f"⚠ Warning: Could not initialize model backends: {e}")
    print("  Falling back to direct Gemini API if available...")
    MODEL = None
    
    # Fallback to direct Gemini API
    try:
        import google.generativeai as genai
        API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if API_KEY:
            genai.configure(api_key=API_KEY)
            GEMINI_MODEL = "gemini-2.0-flash"
            print("✓ Using fallback Gemini API")
        else:
            raise ImproperlyConfigured("No AI model available")
    except Exception as fallback_error:
        raise ImproperlyConfigured(
            f"No AI model backend available: {fallback_error}\n"
            "Please configure one of:\n"
            "1. Set GEMINI_API_KEY in .env file\n"
            "2. Install Ollama from https://ollama.ai/\n"
            "3. Install transformers: pip install transformers torch"
        )

# Try to import magic for file validation
MAGIC_AVAILABLE = False
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    pass

# Load spaCy model
try:
    NLP = spacy.load("en_core_web_sm")
except OSError:
    raise ImproperlyConfigured("spaCy English model not found. Please install it with: python -m spacy download en_core_web_sm")

def validate_file_type(file_path: str, allowed_types: Optional[List[str]] = None) -> bool:
    """Validate file type using magic numbers or extension"""
    allowed_types = allowed_types or getattr(settings, 'ALLOWED_FILE_TYPES', ['pdf', 'docx', 'doc'])
    
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
            'doc': 'application/msword'
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
    """Helper function with retry logic for AI model calls"""
    for attempt in range(max_retries):
        try:
            if MODEL:
                # Use model backend system
                response_text = MODEL.generate(prompt, temperature=temperature, max_tokens=max_tokens)
                # Create a response-like object for compatibility
                class Response:
                    def __init__(self, text):
                        self.text = text
                return Response(response_text)
            else:
                # Fallback to direct Gemini API
                import google.generativeai as genai
                model = genai.GenerativeModel(GEMINI_MODEL)
                generation_config = genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )
                response = model.generate_content(prompt, generation_config=generation_config)
                if response.text:
                    return response
                raise ValueError("Empty response from API")
        except Exception as e:
            if attempt == max_retries - 1:
                raise ValidationError(f"AI generation failed after {max_retries} attempts: {str(e)}")
            sleep(2 ** attempt)  # Exponential backoff

def generate_cover_letter_with_gemini(
    resume_text: str,
    jd_text: str,
    custom_prompt: str = ""
) -> str:
    """Generate a cover letter using Gemini model."""
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
        raise ValidationError(f"Failed to generate cover letter: {str(e)}")

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
        raise ValidationError(f"Failed to calculate job fit: {str(e)}")

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
    except Exception:
        # Fallback to basic resources
        return [
            {
                "skill": skill,
                "resources": [
                    {
                        "title": f"Learn {skill.title()}",
                        "url": f"https://example.com/learn-{skill}",
                        "type": "course"
                    },
                    {
                        "title": f"{skill.title()} Tutorial",
                        "url": f"https://example.com/{skill}-tutorial",
                        "type": "tutorial"
                    }
                ]
            }
            for skill in cleaned_skills[:5]  # Limit to 5 skills
        ]
    

def extract_text_from_file(file_path: str) -> str:
    """Extract text from PDF, DOCX, DOC, or TXT files. Use OCR for scanned PDFs."""
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
            text = extract_text(file_path)
            if not text.strip():
                try:
                    # Fallback to OCR for scanned PDFs (requires Tesseract installed)
                    pages = convert_from_path(file_path)
                    text = "\n".join([pytesseract.image_to_string(p) for p in pages])
                except Exception as ocr_error:
                    # OCR failed - likely Tesseract not installed
                    print(f"OCR extraction failed: {ocr_error}")
                    raise ValidationError(
                        "PDF contains no readable text and OCR extraction failed. "
                        "Please provide a text-selectable PDF or convert to DOCX format. "
                        "Note: Tesseract OCR may not be installed on the system."
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

    prompt = f"""
    You are an AI resume parser. Extract the following fields from the resume:
    - name
    - email
    - phone
    - education (as a list of strings)
    - experience (as a list of strings)
    - skills (as a list of short strings, only technical or job-relevant skills)
    - parsed_text (raw cleaned text)

    Return the response as valid JSON like this:
    {{
      "name": "...",
      "email": "...",
      "phone": "...",
      "education": ["..."],
      "experience": ["..."],
      "skills": ["..."],
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
        ).text.strip()

        # Remove code fences if present
        match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", response)
        cleaned = match.group(1) if match else response

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

        return parsed

    except Exception as e:
        raise ValidationError(f"Error parsing resume with Gemini: {str(e)}")


def enrich_parsed_resume(data: dict, fallback_text: str = "") -> dict:
    text = data.get("parsed_text", fallback_text) or ""

    # Extract email
    if not data.get("email"):
        match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
        data["email"] = match.group(0) if match else ""

    # Extract phone
    if not data.get("phone"):
        match = re.search(r"\+?\d{10,15}", text)
        data["phone"] = match.group(0) if match else ""

    # Extract name (safely first non-empty line)
    if not data.get("name"):
        first_line = ""
        for line in text.splitlines():
            line = line.strip()
            if line and "@" not in line and not line.startswith("+"):
                first_line = line
                break
        data["name"] = first_line

    # Extract education
    if not data.get("education"):
        edu_matches = re.findall(r"(Bachelor|Master|B\.?Tech|MCA|BCA|BSc|MSc).*", text, re.I)
        data["education"] = list(set([e.strip() for e in edu_matches]))

    # Extract skills
    if not data.get("skills"):
        data["skills"] = extract_skills_from_text(text)

    return data


def extract_skills_from_text(text: str) -> List[str]:
    """Extract skills from text using NLP and pattern matching."""
    if not text:
        return []
    
    try:
        doc = NLP(text.lower())
        skills = set()
        
        # Skill patterns
        patterns = [
            r'\b(python|java|javascript|react|angular|vue|node\.?js|django|flask|spring)\b',
            r'\b(sql|mongodb|postgresql|mysql|aws|azure|gcp|docker|kubernetes|git|jenkins)\b',
            r'\b(agile|scrum|html|css|bootstrap|jquery|ajax|rest|api|json|xml|soap|graphql)\b',
            r'\b(machine learning|ml|ai|deep learning|neural networks|tensorflow|pytorch|scikit-learn)\b',
            r'\b(project management|leadership|communication|problem solving|analytical thinking)\b'
        ]
        
        # Pattern matching
        for pattern in patterns:
            skills.update(re.findall(pattern, text.lower()))
        
        # Noun phrases
        for chunk in doc.noun_chunks:
            if len(chunk.text.split()) <= 3:
                skills.add(chunk.text.lower())
        
        return sorted(skills)[:20]  # Return sorted and limited list
    except Exception as e:
        raise ValidationError(f"Failed to extract skills: {str(e)}")

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
        raise ValidationError(f"Failed to calculate ATS score: {str(e)}")