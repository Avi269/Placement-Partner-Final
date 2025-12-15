"""
============================================================================
CORE VIEWS - API Endpoints & Template Views
============================================================================
This module contains all API viewsets and template views for the placement
partner application.

ViewSets (REST API):
- ResumeViewSet: Upload, parse, and optimize resumes
- JobDescriptionViewSet: Manage job postings
- CoverLetterViewSet: Generate AI-powered cover letters
- OfferLetterViewSet: Analyze job offers
- SkillGapReportViewSet: Match resumes with jobs, find skill gaps

Template Views (Web Interface):
- home: Landing page
- resume_upload_view: Resume upload interface
- job_matching_view: Job matching interface
- cover_letter_view: Cover letter generation interface
- offer_analysis_view: Offer letter analysis interface
============================================================================
"""

# Django REST Framework imports
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

# Django core imports
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

# Standard library imports
import tempfile
import os
import json
import logging
import re

# Third-party imports
import google.generativeai as genai

# Local imports - models
from .models import Resume, JobDescription, CoverLetter, OfferLetter, SkillGapReport

# Local imports - serializers
from .serializers import (
    ResumeSerializer, JobDescriptionSerializer, CoverLetterSerializer,
    OfferLetterSerializer, SkillGapReportSerializer,
    ResumeUploadSerializer, JobMatchSerializer, CoverLetterGenerateSerializer,
    OfferLetterAnalyzeSerializer, ATSOptimizeSerializer
)

# Local imports - utility functions
from .utils import (
    parse_resume_file,  # Parse PDF/DOCX resumes
    optimize_resume_for_ats,  # Make resume ATS-friendly
    calculate_user_readiness_score,  # Calculate job readiness
    extract_skills_from_text,  # Extract skills from text
    generate_cover_letter_with_gemini,  # AI cover letter generation
    analyze_offer_letter_with_gemini,  # AI offer analysis
    calculate_job_fit_with_gemini,  # Calculate job fit score
    get_learning_resources_with_gemini,  # Get learning recommendations
    extract_text_from_file,  # Extract text from files
    calculate_ats_score,  # Calculate ATS compatibility score
    calculate_job_fit_with_fallback,    # ✅ Add this new import
)

# Local imports - job search
from .job_search import fetch_jobs_for_skills  # Fetch real job postings

# ============================================================================
# VIEWSETS - REST API ENDPOINTS
# ============================================================================

class ResumeViewSet(viewsets.ModelViewSet):
    """ViewSet for managing resumes via REST API - Anonymous uploads only"""
    queryset = Resume.objects.all()
    serializer_class = ResumeSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    @action(detail=False, methods=['post'])
    def upload(self, request):
        """Upload and parse resume file or text"""
        serializer = ResumeUploadSerializer(data=request.data)
        if serializer.is_valid():
            # Always save as anonymous user
            resume = serializer.save(user=None)
            
            if resume.file:
                file_path = resume.file.path
                try:
                    # Use AI to parse resume file
                    parsed_data = parse_resume_file(file_path)
                    logging.info(f"Parsed resume data: {parsed_data}")
                except Exception as e:
                    logging.exception("Resume parsing failed")
                    return Response({"error": f"Resume parsing failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                # Update resume with parsed data
                resume.parsed_text = parsed_data.get('parsed_text', '')
                resume.name = parsed_data.get('name', '')
                resume.email = parsed_data.get('email', '')
                resume.phone = parsed_data.get('phone', '')
                resume.extracted_skills = parsed_data.get('skills', [])
                resume.education = parsed_data.get('education', [])
                resume.experience = parsed_data.get('experience', [])
                
                # If no skills found, try to extract from text
                if not resume.extracted_skills and resume.parsed_text:
                    resume.extracted_skills = extract_skills_from_text(resume.parsed_text)
                
                resume.save()

                # ✅ Always save resume in session (no auth check)
                request.session["resume_id"] = resume.id

            elif resume.parsed_text and not resume.extracted_skills:
                # Extract skills from provided text
                resume.extracted_skills = extract_skills_from_text(resume.parsed_text)
                resume.save()
            
            return Response(ResumeSerializer(resume).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate ATS-optimized resume"""
        serializer = ATSOptimizeSerializer(data=request.data)
        if serializer.is_valid():
            resume = get_object_or_404(Resume, id=serializer.validated_data['resume_id'])
            
            job_description_text = ""
            if 'job_description_id' in serializer.validated_data:
                jd = get_object_or_404(JobDescription, id=serializer.validated_data['job_description_id'])
                job_description_text = jd.text
            
            # Optimize resume for ATS
            optimized_text = optimize_resume_for_ats(resume.parsed_text, job_description_text)
            
            return Response({
                'resume_id': resume.id,
                'optimized_text': optimized_text,
                'original_text': resume.parsed_text
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def perform_create(self, serializer):
        """Always create resume without user"""
        serializer.save(user=None)

class JobDescriptionViewSet(viewsets.ModelViewSet):
    queryset = JobDescription.objects.all()
    serializer_class = JobDescriptionSerializer

    def perform_create(self, serializer):
        """Create job description without user"""
        serializer.save(user=None)

class CoverLetterViewSet(viewsets.ModelViewSet):
    queryset = CoverLetter.objects.all()
    serializer_class = CoverLetterSerializer

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate cover letter"""
        serializer = CoverLetterGenerateSerializer(data=request.data)
        if serializer.is_valid():
            resume = get_object_or_404(Resume, id=serializer.validated_data['resume_id'])
            jd = get_object_or_404(JobDescription, id=serializer.validated_data['job_description_id'])
            custom_prompt = serializer.validated_data.get('custom_prompt', '')
            
            # Generate cover letter using AI
            cover_letter_text = generate_cover_letter_with_gemini(
                resume.parsed_text, 
                jd.text, 
                custom_prompt
            )
            
            # Save cover letter
            cover_letter = CoverLetter.objects.create(
                resume=resume,
                job_description=jd,
                generated_text=cover_letter_text
            )
            
            return Response(CoverLetterSerializer(cover_letter).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OfferLetterViewSet(viewsets.ModelViewSet):
    queryset = OfferLetter.objects.all()
    serializer_class = OfferLetterSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    @action(detail=False, methods=['post'])
    def explain(self, request):
        """Analyze offer letter"""
        serializer = OfferLetterAnalyzeSerializer(data=request.data)
        if serializer.is_valid():
            # Save without user
            offer_letter = serializer.save(user=None)
            
            # Extract text from file or use provided text
            offer_text = offer_letter.text or ""
            if offer_letter.file:
                offer_text = extract_text_from_file(offer_letter.file.path)
            
            # Analyze offer letter using AI
            analysis = analyze_offer_letter_with_gemini(offer_text)
            
            # Update offer letter with analysis
            offer_letter.explanation = analysis.get('explanation', '')
            offer_letter.risk_flags = analysis.get('risk_flags', [])
            offer_letter.ctc = analysis.get('ctc', '')
            offer_letter.probation_period = analysis.get('probation_period', '')
            offer_letter.notice_period = analysis.get('notice_period', '')
            offer_letter.save()
            
            return Response(OfferLetterSerializer(offer_letter).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SkillGapReportViewSet(viewsets.ModelViewSet):
    queryset = SkillGapReport.objects.all()
    serializer_class = SkillGapReportSerializer

    @action(detail=False, methods=['post'])
    def match(self, request):
        """Match resume with job description and calculate fit score"""
        serializer = JobMatchSerializer(data=request.data)
        if serializer.is_valid():
            resume = get_object_or_404(Resume, id=serializer.validated_data['resume_id'])
            jd = get_object_or_404(JobDescription, id=serializer.validated_data['job_description_id'])
            
            # Calculate job fit
            fit_score, missing_skills, matching_skills = calculate_job_fit_with_gemini(
                resume.extracted_skills, 
                jd.required_skills + jd.preferred_skills
            )
            
            # Get learning resources for missing skills
            suggested_resources = get_learning_resources_with_gemini(missing_skills)
            
            # Save skill gap report
            skill_gap_report = SkillGapReport.objects.create(
                resume=resume,
                job_description=jd,
                fit_score=fit_score,
                missing_skills=missing_skills,
                matching_skills=matching_skills,
                suggested_resources=suggested_resources
            )
            
            return Response(SkillGapReportSerializer(skill_gap_report).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def gaps(self, request):
        """Get missing skills and learning resources"""
        resume_id = request.query_params.get('resume_id')
        jd_id = request.query_params.get('job_description_id')
        
        if resume_id and jd_id:
            try:
                skill_gap_report = SkillGapReport.objects.get(
                    resume_id=resume_id,
                    job_description_id=jd_id
                )
                return Response({
                    'missing_skills': skill_gap_report.missing_skills,
                    'suggested_resources': skill_gap_report.suggested_resources,
                    'fit_score': skill_gap_report.fit_score
                })
            except SkillGapReport.DoesNotExist:
                return Response({'error': 'Skill gap report not found'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({'error': 'resume_id and job_description_id are required'}, status=status.HTTP_400_BAD_REQUEST)


# Additional API views
@api_view(['GET'])
def api_root(request):
    """API root endpoint"""
    return Response({
        'resume_upload': '/resume/upload/',
        'resume_generate': '/resume/generate/',
        'cover_letter': '/cover-letter/generate/',
        'job_match': '/skill-gap-report/match/',
        'skills_gaps': '/skill-gap-report/gaps/',
        'offer_explain': '/offer-letter/explain/',
        'user_profile': '/user-profile/profile/',
    })

# Template Views
def home(request):
    """Home page view"""
    return render(request, 'core/home.html')

@csrf_exempt
def resume_upload_view(request):
    if request.method == 'GET':
        return render(request, 'core/resume_upload.html')

    elif request.method == 'POST':
        resume_file = request.FILES.get('resume')
        parsed_text = request.POST.get('parsed_text', '').strip()
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()

        # Validate input
        if not resume_file and not parsed_text:
            return JsonResponse({
                "success": False, 
                "message": "Please upload a resume file or paste resume text."
            })

        try:
            parsed_data = {}
            
            if resume_file:
                # Save uploaded file temporarily
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(resume_file.name)[-1]) as temp_file:
                    for chunk in resume_file.chunks():
                        temp_file.write(chunk)
                    temp_file_path = temp_file.name

                try:
                    # Parse resume from file
                    parsed_data = parse_resume_file(temp_file_path)
                    logging.info("AI parsing successful")
                except Exception as parse_error:
                    logging.error(f"AI parsing failed: {parse_error}")
                    logging.info("Attempting fallback extraction with regex...")
                    
                    # Fallback: Extract text and use regex-based parsing
                    try:
                        from .utils import extract_text_from_file, enrich_parsed_resume
                        extracted_text = extract_text_from_file(temp_file_path)
                        
                        # Start with manual input or empty data
                        parsed_data = {
                            "name": name,
                            "email": email,
                            "phone": phone,
                            "parsed_text": extracted_text,
                            "skills": [],
                            "education": [],
                            "experience": []
                        }
                        
                        # Apply enrichment to extract missing fields
                        parsed_data = enrich_parsed_resume(parsed_data, fallback_text=extracted_text)
                        logging.info(f"Fallback extraction complete: name={parsed_data.get('name')}, email={parsed_data.get('email')}, skills={len(parsed_data.get('skills', []))}")
                        
                    except Exception as fallback_error:
                        logging.error(f"Fallback extraction also failed: {fallback_error}")
                        parsed_data = {
                            "name": name,
                            "email": email,
                            "phone": phone,
                            "parsed_text": "",
                            "skills": [],
                            "education": [],
                            "experience": []
                        }
                finally:
                    # Delete temp file
                    try:
                        os.remove(temp_file_path)
                    except:
                        pass
            
            elif parsed_text:
                # Parse from text directly
                try:
                    # Create a temporary file with the text
                    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as temp_file:
                        temp_file.write(parsed_text)
                        temp_file_path = temp_file.name
                    
                    # Use Gemini to parse the text
                    prompt = f"""
                    You are an AI resume parser. Extract the following fields from the resume:
                    - name: Full name (ONLY human names, NOT colleges/departments)
                    - email: Email address
                    - phone: Phone number
                    - education: Educational qualifications as a list (include degree, institution, year)
                    - experience: Work experience ONLY (job roles at companies with duration). DO NOT include education dates or course duration.
                    - skills: Technical and job-relevant skills only (as a list of short strings)
                    - parsed_text: Raw cleaned text

                    IMPORTANT for "experience":
                    - ONLY extract actual work experience (jobs at companies)
                    - DO NOT extract education duration (e.g., "2020-2023" from college)
                    - Each entry needs: Job Title + Company + Duration
                    - If no work experience, return empty list []

                    Return the response as valid JSON.

                    Resume:
                    {parsed_text}
                    """
                    
                    from .utils import generate_with_retry
                    import re
                    
                    response = generate_with_retry(
                        prompt,
                        temperature=0.0,
                        max_tokens=1024
                    )

                    # Extract text from response
                    response_text = response.text.strip()

                    # Remove code fences if present
                    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", response_text)
                    cleaned = match.group(1) if match else response_text
                    
                    parsed_data = json.loads(cleaned) if cleaned else {}
                    
                    # Enrich parsed data with fallback extraction
                    from .utils import enrich_parsed_resume
                    parsed_data = enrich_parsed_resume(parsed_data, fallback_text=parsed_text)
                    
                    # Clean up temp file
                    try:
                        os.remove(temp_file_path)
                    except:
                        pass
                    
                except Exception as text_parse_error:
                    logging.error(f"AI text parsing failed: {text_parse_error}")
                    logging.info("Attempting fallback enrichment for text...")
                    
                    # Fallback: Use enrichment
                    from .utils import enrich_parsed_resume
                    parsed_data = {
                        "name": name,
                        "email": email,
                        "phone": phone,
                        "parsed_text": parsed_text,
                        "skills": [],
                        "education": [],
                        "experience": []
                    }
                    parsed_data = enrich_parsed_resume(parsed_data, fallback_text=parsed_text)
                    logging.info(f"Fallback enrichment complete: name={parsed_data.get('name')}, email={parsed_data.get('email')}, skills={len(parsed_data.get('skills', []))}")

            # Override with manually provided data if available (user input takes precedence)
            if name:
                parsed_data["name"] = name
            if email:
                parsed_data["email"] = email
            if phone:
                parsed_data["phone"] = phone

            # Ensure all required fields exist
            parsed_data.setdefault("name", "")
            parsed_data.setdefault("email", "")
            parsed_data.setdefault("phone", "")
            parsed_data.setdefault("parsed_text", parsed_text or "")
            parsed_data.setdefault("skills", [])
            parsed_data.setdefault("education", [])
            parsed_data.setdefault("experience", [])
            
            # Ensure skills is a list, not a string
            if isinstance(parsed_data["skills"], str):
                # If it's a comma-separated string
                if ',' in parsed_data["skills"]:
                    parsed_data["skills"] = [s.strip() for s in parsed_data["skills"].split(',') if s.strip()]
                # If it's a space-separated string
                elif ' ' in parsed_data["skills"]:
                    parsed_data["skills"] = [s.strip() for s in parsed_data["skills"].split() if s.strip() and len(s.strip()) > 1]
                # Otherwise treat the whole string as a single skill
                else:
                    parsed_data["skills"] = [parsed_data["skills"].strip()] if parsed_data["skills"].strip() else []
            
            # Additional validation: ensure each skill is a string with reasonable length
            if isinstance(parsed_data["skills"], list):
                validated_skills = []
                for skill in parsed_data["skills"]:
                    if isinstance(skill, str) and len(skill) > 1 and len(skill) < 50:
                        validated_skills.append(skill.strip())
                parsed_data["skills"] = validated_skills
            
            # Log parsed data for debugging
            logging.info(f"Final parsed data: name='{parsed_data.get('name')}', email='{parsed_data.get('email')}', phone='{parsed_data.get('phone')}', skills={parsed_data.get('skills', [])}, skills_count={len(parsed_data.get('skills', []))}")

            # Save resume (always anonymous)
            resume = Resume.objects.create(
                user=None,  # No user association
                file=resume_file if resume_file else None,
                name=parsed_data.get("name", ""),
                email=parsed_data.get("email", ""),
                phone=parsed_data.get("phone", ""),
                parsed_text=parsed_data.get("parsed_text", ""),
                extracted_skills=parsed_data.get("skills", []),
                education=parsed_data.get("education", []),
                experience=parsed_data.get("experience", [])
            )

            # Always save resume ID in session for anonymous tracking
            request.session["resume_id"] = resume.id
            
            # Calculate ATS score (now includes automatic fallback)
            ats_data = {}
            recommended_jobs = []
            
            try:
                ats_data = calculate_ats_score(
                    parsed_data.get("parsed_text", ""), 
                    parsed_data.get("skills", [])
                )
                logging.info(f"ATS score calculated: {ats_data.get('ats_score')}")
            except Exception as e:
                logging.error(f"ATS calculation completely failed (both AI and fallback): {e}")
                # Only if both AI and fallback fail (very rare)
                ats_data = {
                    "ats_score": 70,
                    "keyword_match": 65,
                    "format_score": 75,
                    "content_score": 70,
                    "strengths": ["Resume uploaded successfully"],
                    "weaknesses": ["Unable to perform detailed analysis at this time"],
                    "suggestions": ["Please try again later or contact support if the issue persists"]
                }
            
            # Fetch job recommendations based on skills
            try:
                recommended_jobs = fetch_jobs_for_skills(
                    parsed_data.get("skills", [])[:10],
                    max_results=10
                ) if parsed_data.get("skills") else []
                logging.info(f"Fetched {len(recommended_jobs)} recommended jobs")
                if recommended_jobs:
                    logging.info(f"Sample job: {recommended_jobs[0].get('title', 'N/A')} at {recommended_jobs[0].get('company', 'N/A')}")
                else:
                    logging.warning("No jobs were returned from APIs")
            except Exception as e:
                logging.exception(f"Job fetch failed with exception: {e}")

            # Check if we had to use fallback extraction (AI quota exceeded)
            ai_fallback_used = False
            warning_message = ""
            
            # Check logs for quota-related errors
            import logging as log_module
            if hasattr(log_module, '_nameToLevel'):
                # Check if extraction quality might be affected
                if not parsed_data.get("name") or not parsed_data.get("email"):
                    warning_message = "Note: Basic extraction was used. Some fields may be missing. For best results, please ensure your resume is well-formatted or try again later."
                elif parsed_data.get("skills") and len(parsed_data.get("skills", [])) < 3:
                    warning_message = "Note: Limited skills were extracted. Consider reviewing the extracted information."

            response_data = {
                "success": True,
                "data": parsed_data,
                "resume_id": resume.id,
                "ats_analysis": ats_data,
                "recommended_jobs": recommended_jobs
            }
            
            # Add warning if fallback was used
            if warning_message:
                response_data["warning"] = warning_message
            
            return JsonResponse(response_data)

        except ValidationError as ve:
            logging.error(f"Validation error: {ve}")
            return JsonResponse({
                "success": False,
                "message": str(ve)
            })
        except Exception as e:
            logging.exception("Error processing resume")
            return JsonResponse({
                "success": False,
                "message": "Error processing resume. Please try again or contact support.",
                "error": str(e)
            })

    else:
        return JsonResponse({"success": False, "message": "Invalid request method."})

@csrf_exempt
def job_matching_view(request):
    if request.method == 'GET':
        # ✅ Get resume from session only (no auth check)
        resume = None
        resume_id = request.session.get("resume_id")
        if resume_id:
            resume = Resume.objects.filter(id=resume_id).first()
        
        # Fetch recommended jobs immediately on page load
        recommended_jobs = []
        if resume and resume.extracted_skills:
            try:
                recommended_jobs = fetch_jobs_for_skills(
                    resume.extracted_skills,
                    location="in",
                    max_results=10
                )
                logging.info(f"Loaded {len(recommended_jobs)} jobs for page display")
            except Exception as e:
                logging.error(f"Error fetching jobs for page load: {e}")
        
        context = {
            'resume': resume,
            'has_resume': resume is not None,
            'recommended_jobs': recommended_jobs
        }
        return render(request, 'core/job_matching.html', context)

    elif request.method == 'POST':
        try:
            data = request.POST
            jd_text = data.get("description", "").strip()
            
            if not jd_text:
                return JsonResponse({
                    "success": False, 
                    "message": "Please provide a job description"
                })
            
            logging.info(f"Job matching request received. JD length: {len(jd_text)}")

            # Get resume from session
            resume_id = request.session.get("resume_id")
            logging.info(f"Session resume_id: {resume_id}")
            resume = Resume.objects.filter(id=resume_id).first() if resume_id else None

            if not resume:
                logging.warning("No resume found for job matching")
                return JsonResponse({
                    "success": False, 
                    "message": "No resume found. Please upload your resume first."
                })

            if not resume.extracted_skills:
                logging.warning("Resume has no extracted skills")
                return JsonResponse({
                    "success": False,
                    "message": "Your resume has no extracted skills. Please re-upload with a better formatted resume."
                })
            
            logging.info(f"Resume skills ({len(resume.extracted_skills)}): {resume.extracted_skills[:10]}")
            
            # Calculate job fit (has built-in fallback)
            try:
                fit_score, matching_skills, missing_skills = calculate_job_fit_with_gemini(
                    resume.extracted_skills,
                    jd_text
                )
                logging.info(f"✅ Job fit calculated: {fit_score}% (matching: {len(matching_skills)}, missing: {len(missing_skills)})")
            except Exception as match_error:
                logging.error(f"Job matching completely failed: {match_error}")
                # Last resort fallback
                fit_score, matching_skills, missing_skills = calculate_job_fit_with_fallback(
                    resume.extracted_skills,
                    jd_text
                )
                logging.info(f"✅ Fallback job fit: {fit_score}%")
            
            # Ensure we have at least some data
            if not matching_skills and not missing_skills:
                logging.warning("Both matching and missing skills are empty, creating defaults")
                # If everything failed, at least show resume skills
                matching_skills = resume.extracted_skills[:10]
                missing_skills = ["Technical Skills", "Communication", "Problem Solving"]
                fit_score = 50.0
            
            # Calculate experience match
            experience_match = calculate_experience_match(resume, jd_text)
            
            # Calculate education match
            education_match = calculate_education_match(resume, jd_text)
            
            # Get learning resources for missing skills
            learning_resources = []
            if missing_skills:
                try:
                    learning_resources = get_learning_resources_with_gemini(missing_skills[:5])
                    logging.info(f"✅ Generated {len(learning_resources)} learning resource groups")
                except Exception as lr_error:
                    logging.error(f"Learning resources failed: {lr_error}")
                    # Fallback: Generate basic YouTube links
                    learning_resources = [
                        {
                            "skill": skill,
                            "resources": [
                                {
                                    "title": f"Learn {skill} - YouTube Tutorials",
                                    "url": f"https://www.youtube.com/results?search_query={skill.replace(' ', '+')}+tutorial+2024",
                                    "type": "Video",
                                    "description": f"Comprehensive video tutorials on {skill}",
                                    "duration": "Varies"
                                },
                                {
                                    "title": f"{skill} Documentation",
                                    "url": f"https://www.google.com/search?q={skill.replace(' ', '+')}+official+documentation",
                                    "type": "Documentation",
                                    "description": f"Official documentation and guides",
                                    "duration": "Self-paced"
                                }
                            ]
                        }
                        for skill in missing_skills[:5]
                    ]

            # Fetch recommended jobs
            recommended_jobs = []
            try:
                if resume.extracted_skills:
                    recommended_jobs = fetch_jobs_for_skills(
                        resume.extracted_skills[:10],
                        location="in",
                        max_results=10
                    )
                    logging.info(f"✅ Found {len(recommended_jobs)} recommended jobs")
            except Exception as job_error:
                logging.error(f"Job fetching failed: {job_error}")

            # Calculate overall weighted fit score
            overall_fit_score = int((fit_score * 0.5) + (experience_match * 0.3) + (education_match * 0.2))
            
            response_data = {
                "success": True,
                "fit_score": overall_fit_score,
                "skills_match": int(fit_score),
                "experience_match": experience_match,
                "education_match": education_match,
                "matching_skills": matching_skills,
                "missing_skills": missing_skills,
                "resume_data": {
                    "name": resume.name or "Not provided",
                    "email": resume.email or "Not provided",
                    "phone": resume.phone or "Not provided",
                    "all_skills": resume.extracted_skills or []
                },
                "recommendations": {
                    "skills_to_develop": missing_skills,
                    "learning_resources": learning_resources,
                    "resume_improvements": []
                },
                "recommended_jobs": recommended_jobs
            }
            
            logging.info(f"✅ Sending response: {len(matching_skills)} matching, {len(missing_skills)} missing, {len(learning_resources)} resources")
            return JsonResponse(response_data)

        except Exception as e:
            logging.exception("Job matching error")
            return JsonResponse({
                "success": False, 
                "message": f"Error analyzing job match: {str(e)}"
            })


@csrf_exempt
def cover_letter_view(request):
    """Cover letter generation view"""
    if request.method == 'GET':
        # Get resume from session
        resume = None
        resume_id = request.session.get("resume_id")
        if resume_id:
            resume = Resume.objects.filter(id=resume_id).first()
        
        # Fetch recommended jobs for cover letter
        recommended_jobs = []
        if resume and resume.extracted_skills:
            try:
                recommended_jobs = fetch_jobs_for_skills(
                    resume.extracted_skills[:10],
                    location="in",
                    max_results=10
                )
                logging.info(f"Loaded {len(recommended_jobs)} jobs for cover letter page")
            except Exception as e:
                logging.error(f"Error fetching jobs: {e}")
        
        context = {
            'resume': resume,
            'has_resume': resume is not None,
            'recommended_jobs': recommended_jobs
        }
        return render(request, 'core/cover_letter.html', context)
    
    elif request.method == 'POST':
        try:
            # Try to parse JSON first, then fall back to form data
            if request.content_type == 'application/json':
                try:
                    data = json.loads(request.body)
                except json.JSONDecodeError:
                    data = request.POST
            else:
                data = request.POST
            
            # Get form data with multiple possible field names
            job_title = (
                data.get('job_title') or 
                data.get('jobTitle') or 
                data.get('title') or 
                ''
            ).strip()
            
            company = (
                data.get('company') or 
                data.get('company_name') or 
                data.get('companyName') or 
                ''
            ).strip()
            
            job_description = (
                data.get('job_description') or 
                data.get('jobDescription') or 
                data.get('description') or 
                ''
            ).strip()
            
            custom_prompt = (
                data.get('custom_prompt') or 
                data.get('customPrompt') or 
                data.get('additional_notes') or 
                ''
            ).strip()
            
            # Debug logging
            logging.info(f"Cover letter request - Title: '{job_title}', Company: '{company}', JD length: {len(job_description)}")
            logging.info(f"Request content type: {request.content_type}")
            logging.info(f"POST data keys: {list(data.keys())}")
            
            # Validation
            if not job_title:
                return JsonResponse({
                    "success": False,
                    "message": "Please provide a job title"
                })
            
            if not company:
                return JsonResponse({
                    "success": False,
                    "message": "Please provide a company name"
                })
            
            if not job_description:
                return JsonResponse({
                    "success": False,
                    "message": "Please provide a job description"
                })
            
            # Get resume from session
            resume_id = request.session.get("resume_id")
            logging.info(f"Session resume_id: {resume_id}")
            
            resume = Resume.objects.filter(id=resume_id).first() if resume_id else None
            
            if not resume:
                return JsonResponse({
                    "success": False,
                    "message": "No resume found. Please upload your resume first."
                })
            
            if not resume.parsed_text and not resume.extracted_skills:
                return JsonResponse({
                    "success": False,
                    "message": "Your resume has no content. Please re-upload your resume."
                })
            
            # Generate cover letter using AI
            try:
                cover_letter_text = generate_cover_letter_with_gemini(
                    resume_text=resume.parsed_text or " ".join(resume.extracted_skills),
                    jd_text=f"Job Title: {job_title}\nCompany: {company}\n\n{job_description}",
                    custom_prompt=custom_prompt,
                    applicant_name=resume.name or "Applicant",
                    applicant_email=resume.email or "",
                    job_title=job_title,
                    company_name=company
                )
                
                logging.info(f"✅ Cover letter generated successfully ({len(cover_letter_text)} chars)")
                
                # Save cover letter
                cover_letter = CoverLetter.objects.create(
                    resume=resume,
                    job_description=None,  # Not linked to JobDescription model
                    generated_text=cover_letter_text
                )
                
                return JsonResponse({
                    "success": True,
                    "cover_letter": cover_letter_text,
                    "cover_letter_id": cover_letter.id,
                    "message": "Cover letter generated successfully!"
                })
                
            except ValidationError as ve:
                logging.error(f"Cover letter validation error: {ve}")
                return JsonResponse({
                    "success": False,
                    "message": str(ve)
                })
            except Exception as gen_error:
                logging.error(f"Cover letter generation failed: {gen_error}")
                return JsonResponse({
                    "success": False,
                    "message": "Failed to generate cover letter. Please try again or contact support."
                })
        
        except Exception as e:
            logging.exception("Cover letter generation error")
            return JsonResponse({
                "success": False,
                "message": f"Error generating cover letter: {str(e)}"
            })


@csrf_exempt
def offer_analysis_view(request):
    """Offer letter analysis view"""
    if request.method == 'GET':
        return render(request, 'core/offer_analysis.html')
    
    elif request.method == 'POST':
        try:
            # Get offer letter file or text
            offer_file = request.FILES.get('offer_file')
            offer_text = request.POST.get('offer_text', '').strip()
            
            if not offer_file and not offer_text:
                return JsonResponse({
                    "success": False,
                    "message": "Please upload an offer letter file or paste the text"
                })
            
            # Extract text from file if provided
            extracted_text = ""
            if offer_file:
                # Save file temporarily
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(offer_file.name)[-1]) as temp_file:
                    for chunk in offer_file.chunks():
                        temp_file.write(chunk)
                    temp_file_path = temp_file.name
                
                try:
                    extracted_text = extract_text_from_file(temp_file_path)
                finally:
                    try:
                        os.remove(temp_file_path)
                    except:
                        pass
            else:
                extracted_text = offer_text
            
            if not extracted_text:
                return JsonResponse({
                    "success": False,
                    "message": "Could not extract text from the offer letter"
                })
            
            # Analyze offer letter using AI
            try:
                analysis = analyze_offer_letter_with_gemini(extracted_text)
                
                # Save offer letter analysis
                offer_letter = OfferLetter.objects.create(
                    user=None,
                    file=offer_file if offer_file else None,
                    text=extracted_text if not offer_file else "",
                    explanation=analysis.get('explanation', ''),
                    risk_flags=analysis.get('risk_flags', []),
                    ctc=analysis.get('ctc', ''),
                    probation_period=analysis.get('probation_period', ''),
                    notice_period=analysis.get('notice_period', '')
                )
                
                return JsonResponse({
                    "success": True,
                    "analysis": {
                        "explanation": analysis.get('explanation', ''),
                        "risk_flags": analysis.get('risk_flags', []),
                        "ctc": analysis.get('ctc', 'Not specified'),
                        "probation_period": analysis.get('probation_period', 'Not specified'),
                        "notice_period": analysis.get('notice_period', 'Not specified'),
                        "benefits": analysis.get('benefits', []),
                        "key_terms": analysis.get('key_terms', [])
                    },
                    "offer_letter_id": offer_letter.id
                })
                
            except Exception as analysis_error:
                logging.error(f"Offer analysis failed: {analysis_error}")
                return JsonResponse({
                    "success": False,
                    "message": "Failed to analyze offer letter. Please try again."
                })
        
        except Exception as e:
            logging.exception("Offer analysis error")
            return JsonResponse({
                "success": False,
                "message": f"Error analyzing offer letter: {str(e)}"
            })


# Helper functions remain at the end
def calculate_experience_match(resume, jd_text: str) -> int:
    """Calculate experience match percentage"""
    jd_lower = jd_text.lower()
    
    # Extract years from JD
    import re
    exp_patterns = [
        r'(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience',
        r'experience\s+of\s+(\d+)\+?\s*(?:years?|yrs?)',
        r'minimum\s+(\d+)\+?\s*(?:years?|yrs?)'
    ]
    required_years = 0
    for pattern in exp_patterns:
        match = re.search(pattern, jd_lower)
        if match:
            required_years = int(match.group(1))
            break
    
    # Extract years from resume
    resume_years = 0
    if resume.experience:
        for exp in resume.experience:
            exp_str = str(exp).lower()
            year_match = re.search(r'(\d+)\+?\s*(?:years?|yrs?)', exp_str)
            if year_match:
                resume_years = max(resume_years, int(year_match.group(1)))
    
    # Calculate match
    if required_years == 0:
        return 75
    elif resume_years >= required_years:
        return 100
    elif resume_years >= required_years * 0.7:
        return 80
    elif resume_years >= required_years * 0.5:
        return 60
    else:
        return max(30, int((resume_years / required_years) * 100))


def calculate_education_match(resume, jd_text: str) -> int:
    """Calculate education match percentage"""
    jd_lower = jd_text.lower()
    
    education_keywords = {
        'phd': ['phd', 'ph.d', 'doctorate', 'doctoral'],
        'masters': ['masters', 'master', 'm.tech', 'mtech', 'm.sc', 'msc', 'mba', 'ms'],
        'bachelors': ['bachelors', 'bachelor', 'b.tech', 'btech', 'b.sc', 'bsc', 'b.e', 'be', 'bca', 'bba'],
        'diploma': ['diploma', 'associate']
    }
    
    # Check required education
    required_edu_level = 0
    for level, keywords in education_keywords.items():
        for keyword in keywords:
            if keyword in jd_lower:
                if level == 'phd':
                    required_edu_level = 4
                elif level == 'masters':
                    required_edu_level = max(required_edu_level, 3)
                elif level == 'bachelors':
                    required_edu_level = max(required_edu_level, 2)
                elif level == 'diploma':
                    required_edu_level = max(required_edu_level, 1)
    
    # Check resume education
    resume_edu_level = 0
    if resume.education:
        for edu in resume.education:
            edu_str = str(edu).lower()
            if any(k in edu_str for k in education_keywords['phd']):
                resume_edu_level = 4
            elif any(k in edu_str for k in education_keywords['masters']):
                resume_edu_level = max(resume_edu_level, 3)
            elif any(k in edu_str for k in education_keywords['bachelors']):
                resume_edu_level = max(resume_edu_level, 2)
            elif any(k in edu_str for k in education_keywords['diploma']):
                resume_edu_level = max(resume_edu_level, 1)
    
    # Calculate match
    if required_edu_level == 0:
        return 80
    elif resume_edu_level >= required_edu_level:
        return 100
    elif resume_edu_level == required_edu_level - 1:
        return 70
    elif resume_edu_level > 0:
        return 50
    else:
        return 30