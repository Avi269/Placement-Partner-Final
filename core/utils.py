import re
import json
import os
from typing import Dict, List, Tuple
import spacy
from pyresparser import ResumeParser
import docx2txt
from pdfminer.high_level import extract_text
from django.conf import settings
from django.core.exceptions import ValidationError

# Try to import magic, fallback to basic validation if not available
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    print("Warning: python-magic not available. Using basic file validation.")

def validate_file_type(file_path: str, allowed_types: List[str] = None) -> bool:
    """Validate file type using magic numbers or extension"""
    if allowed_types is None:
        allowed_types = getattr(settings, 'ALLOWED_FILE_TYPES', ['pdf', 'docx', 'doc'])
    
    try:
        file_extension = file_path.split('.')[-1].lower()
        
        if not MAGIC_AVAILABLE:
            # Fallback to extension-only validation
            return file_extension in allowed_types
        
        # Use magic for MIME type validation
        mime = magic.from_file(file_path, mime=True)
        
        # Check both MIME type and extension
        valid_mime_types = {
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'doc': 'application/msword'
        }
        
        return (file_extension in allowed_types and 
                mime == valid_mime_types.get(file_extension))
    except Exception:
        # Fallback to extension-only validation
        try:
            file_extension = file_path.split('.')[-1].lower()
            return file_extension in allowed_types
        except:
            return False

def validate_file_size(file_path: str, max_size: int = None) -> bool:
    """Validate file size"""
    if max_size is None:
        max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 10 * 1024 * 1024)  # 10MB
    
    try:
        file_size = os.path.getsize(file_path)
        return file_size <= max_size
    except Exception:
        return False

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent security issues"""
    # Remove any path traversal attempts
    filename = os.path.basename(filename)
    # Remove special characters
    filename = re.sub(r'[^\w\-_\.]', '', filename)
    return filename

# Mock AI functions (replace with actual Gemini API integration later)
def mock_generate_cover_letter(resume_text: str, jd_text: str, custom_prompt: str = "") -> str:
    """Mock function to generate cover letter using AI"""
    # Validate inputs
    if not resume_text or not jd_text:
        raise ValidationError("Resume text and job description are required")
    
    # Sanitize inputs
    resume_text = resume_text[:2000]  # Limit length
    jd_text = jd_text[:2000]
    custom_prompt = custom_prompt[:500]
    
    prompt = f"""
    Generate a professional cover letter based on the following:
    
    Resume: {resume_text[:1000]}...
    
    Job Description: {jd_text[:1000]}...
    
    Custom Instructions: {custom_prompt}
    
    Make it compelling, professional, and tailored to the job description.
    """
    
    # Mock response
    return f"""
Dear Hiring Manager,

I am writing to express my strong interest in the position at your company. With my background and skills, I believe I would be an excellent fit for this role.

Based on my experience and the requirements outlined in your job description, I am confident that I can contribute effectively to your team. My skills and experience align well with what you're looking for.

I am particularly excited about the opportunity to work in this role and contribute to your organization's success.

Thank you for considering my application. I look forward to discussing how I can add value to your team.

Best regards,
[Your Name]
    """.strip()

def mock_analyze_offer_letter(offer_text: str) -> Dict:
    """Mock function to analyze offer letter using AI"""
    # Validate input
    if not offer_text:
        raise ValidationError("Offer letter text is required")
    
    # Sanitize input
    offer_text = offer_text[:5000]  # Limit length
    
    # Mock analysis
    return {
        "explanation": "This is a standard offer letter with typical terms and conditions.",
        "risk_flags": [
            "Standard probation period",
            "Typical notice period requirements"
        ],
        "ctc": "₹8,00,000 per annum",
        "probation_period": "6 months",
        "notice_period": "60 days",
        "summary": "Overall, this appears to be a standard offer letter with reasonable terms."
    }

def mock_calculate_job_fit(resume_skills: List[str], jd_skills: List[str]) -> Tuple[float, List[str], List[str]]:
    """Mock function to calculate job fit score"""
    # Validate inputs
    if not isinstance(resume_skills, list) or not isinstance(jd_skills, list):
        raise ValidationError("Skills must be provided as lists")
    
    # Sanitize skills
    resume_skills = [str(skill).lower().strip() for skill in resume_skills if skill]
    jd_skills = [str(skill).lower().strip() for skill in jd_skills if skill]
    
    resume_skills_set = set(resume_skills)
    jd_skills_set = set(jd_skills)
    
    matching_skills = list(resume_skills_set.intersection(jd_skills_set))
    missing_skills = list(jd_skills_set - resume_skills_set)
    
    if len(jd_skills_set) == 0:
        fit_score = 0.0
    else:
        fit_score = (len(matching_skills) / len(jd_skills_set)) * 100
    
    return fit_score, missing_skills, matching_skills

def mock_get_learning_resources(missing_skills: List[str]) -> List[Dict]:
    """Mock function to get learning resources for missing skills"""
    # Validate input
    if not isinstance(missing_skills, list):
        raise ValidationError("Missing skills must be provided as a list")
    
    # Sanitize skills
    missing_skills = [str(skill).lower().strip() for skill in missing_skills if skill]
    
    resources = []
    for skill in missing_skills[:5]:  # Limit to 5 skills
        resources.append({
            "skill": skill,
            "resources": [
                {
                    "title": f"Learn {skill.title()}",
                    "url": f"https://example.com/learn-{skill.lower()}",
                    "type": "course"
                },
                {
                    "title": f"{skill.title()} Tutorial",
                    "url": f"https://example.com/{skill.lower()}-tutorial",
                    "type": "tutorial"
                }
            ]
        })
    return resources

def parse_resume_file(file_path: str) -> Dict:
    """Parse resume file and extract information"""
    try:
        # Validate file
        if not os.path.exists(file_path):
            raise ValidationError("File does not exist")
        
        if not validate_file_type(file_path):
            raise ValidationError("Invalid file type")
        
        if not validate_file_size(file_path):
            raise ValidationError("File too large")
        
        # Try using pyresparser first
        parser = ResumeParser(file_path)
        data = parser.get_extracted_data()
        
        # Extract basic information
        parsed_data = {
            'parsed_text': data.get('text', ''),
            'name': data.get('name', ''),
            'email': data.get('email', ''),
            'phone': data.get('mobile_number', ''),
            'skills': data.get('skills', []),
            'education': data.get('education', []),
            'experience': data.get('experience', [])
        }
        
        # If pyresparser fails, try manual extraction
        if not parsed_data['parsed_text']:
            parsed_data['parsed_text'] = extract_text_from_file(file_path)
        
        return parsed_data
        
    except Exception as e:
        # Log error and return empty data
        print(f"Error parsing resume file: {str(e)}")
        return {
            'parsed_text': '',
            'name': '',
            'email': '',
            'phone': '',
            'skills': [],
            'education': [],
            'experience': []
        }

def extract_text_from_file(file_path: str) -> str:
    """Extract text from various file formats"""
    try:
        file_extension = file_path.split('.')[-1].lower()
        
        if file_extension == 'pdf':
            return extract_text(file_path)
        elif file_extension in ['docx', 'doc']:
            return docx2txt.process(file_path)
        else:
            raise ValidationError(f"Unsupported file type: {file_extension}")
            
    except Exception as e:
        print(f"Error extracting text from file: {str(e)}")
        return ""

def extract_skills_from_text(text: str) -> List[str]:
    """Extract skills from text using NLP"""
    try:
        # Load spaCy model
        nlp = spacy.load("en_core_web_sm")
        
        # Process text
        doc = nlp(text.lower())
        
        # Define skill patterns
        skill_patterns = [
            r'\b(python|java|javascript|react|angular|vue|node\.js|django|flask|spring|sql|mongodb|postgresql|mysql|aws|azure|gcp|docker|kubernetes|git|jenkins|agile|scrum)\b',
            r'\b(html|css|bootstrap|jquery|ajax|rest|api|json|xml|soap|graphql|microservices|serverless|lambda|ec2|s3|rds|elasticsearch|redis|kafka|rabbitmq)\b',
            r'\b(machine learning|ml|artificial intelligence|ai|deep learning|neural networks|tensorflow|pytorch|scikit-learn|pandas|numpy|matplotlib|seaborn)\b',
            r'\b(project management|leadership|team management|communication|problem solving|analytical thinking|critical thinking|creativity|adaptability|time management)\b'
        ]
        
        skills = set()
        
        # Extract skills using patterns
        for pattern in skill_patterns:
            matches = re.findall(pattern, text.lower())
            skills.update(matches)
        
        # Extract noun phrases that might be skills
        for chunk in doc.noun_chunks:
            if len(chunk.text.split()) <= 3:  # Single words or short phrases
                skills.add(chunk.text.lower())
        
        return list(skills)[:20]  # Limit to 20 skills
        
    except Exception as e:
        print(f"Error extracting skills: {str(e)}")
        return []

def optimize_resume_for_ats(resume_text: str, job_description: str = "") -> str:
    """Optimize resume for ATS systems"""
    try:
        # Extract keywords from job description
        if job_description:
            job_keywords = extract_skills_from_text(job_description)
        else:
            job_keywords = []
        
        # Extract skills from resume
        resume_skills = extract_skills_from_text(resume_text)
        
        # Create optimized version
        optimized_text = resume_text
        
        # Add missing keywords if they're relevant
        missing_keywords = [kw for kw in job_keywords if kw not in resume_skills]
        
        if missing_keywords:
            optimized_text += f"\n\nAdditional Skills: {', '.join(missing_keywords[:5])}"
        
        return optimized_text
        
    except Exception as e:
        print(f"Error optimizing resume: {str(e)}")
        return resume_text

def extract_key_terms(text: str) -> List[str]:
    """Extract key terms from text"""
    try:
        # Define key term patterns
        patterns = [
            r'\b(CTC|ctc|salary|compensation|package|offer|probation|notice|period|months?|days?|years?)\b',
            r'\b(₹|rs\.?|rupees?|dollars?|\$|euros?|£)\s*\d+[,\d]*\s*(lakhs?|crores?|thousands?|k|m)?',
            r'\b\d+\s*(months?|days?|years?)\s*(probation|notice|period)',
            r'\b(health|insurance|benefits|bonus|stock|options|equity|esop|rsu)',
            r'\b(annual|monthly|weekly|daily|hourly)\s*(leave|vacation|holiday|sick)'
        ]
        
        terms = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            terms.extend(matches)
        
        return list(set(terms))
        
    except Exception as e:
        print(f"Error extracting key terms: {str(e)}")
        return []

def calculate_user_readiness_score(user_profile) -> float:
    """Calculate user readiness score based on profile"""
    try:
        score = 0.0
        
        # Base score
        score += 20.0
        
        # Applications submitted
        if user_profile.total_applications > 0:
            score += min(user_profile.total_applications * 2, 20)
        
        # Interviews attended
        if user_profile.interviews_attended > 0:
            score += min(user_profile.interviews_attended * 5, 30)
        
        # Offers received
        if user_profile.offers_received > 0:
            score += min(user_profile.offers_received * 10, 30)
        
        return min(score, 100.0)
        
    except Exception as e:
        print(f"Error calculating readiness score: {str(e)}")
        return 0.0 