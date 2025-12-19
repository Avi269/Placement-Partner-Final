"""
============================================================================
CORE VIEWS - API Endpoints & Template Views
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
from typing import List, Dict, Tuple, Optional  # ✅ ADD THIS LINE

# Third-party imports
import google.generativeai as genai

# ✅ ADD MISSING LOGGER INITIALIZATION
logger = logging.getLogger(__name__)

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
        """Generate cover letter via API"""
        serializer = CoverLetterGenerateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            resume_id = serializer.validated_data['resume_id']
            jd_text = serializer.validated_data['job_description']
            job_title = serializer.validated_data.get('job_title', 'Position')
            company = serializer.validated_data.get('company', 'Company')
            custom_prompt = serializer.validated_data.get('custom_prompt', '')
            
            resume = Resume.objects.get(id=resume_id)
            
            # Create or get JobDescription
            job_description, created = JobDescription.objects.get_or_create(
                title=job_title,
                company=company,
                description=jd_text[:5000],
                defaults={
                    'location': 'Not specified',
                    'job_type': 'full-time',
                    'salary_range': '',
                    'required_skills': [],
                    'preferred_skills': [],
                }
            )
            
            # Generate cover letter
            cover_letter_text = generate_cover_letter_with_gemini(
                resume_text=resume.parsed_text or "",
                jd_text=jd_text,
                custom_prompt=custom_prompt,
                applicant_name=resume.name or "",
                applicant_email=resume.email or "",
                job_title=job_title,
                company_name=company
            )
            
            # Save to database
            cover_letter = CoverLetter.objects.create(
                resume=resume,
                job_description=job_description,
                content=cover_letter_text,
                custom_prompt=custom_prompt
            )
            
            return Response({
                'success': True,
                'cover_letter_id': cover_letter.id,
                'content': cover_letter_text
            }, status=status.HTTP_201_CREATED)
            
        except Resume.DoesNotExist:
            return Response(
                {'error': 'Resume not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Cover letter generation failed: {e}", exc_info=True)
            return Response(
                {'error': f'Generation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
            
            logging.info(f"📋 Job matching request - JD length: {len(jd_text)}")
            logging.info(f"📋 JD preview: {jd_text[:200]}...")

            # Get resume from session
            resume_id = request.session.get("resume_id")
            resume = Resume.objects.filter(id=resume_id).first() if resume_id else None

            if not resume:
                return JsonResponse({
                    "success": False, 
                    "message": "No resume found. Please upload your resume first."
                })

            if not resume.extracted_skills:
                return JsonResponse({
                    "success": False,
                    "message": "Your resume has no extracted skills. Please re-upload."
                })
            
            logging.info(f"👤 Resume skills ({len(resume.extracted_skills)}): {resume.extracted_skills}")
            
            # Use improved fallback
            try:
                fit_score, matching_skills, missing_skills = calculate_job_fit_with_fallback(
                    resume.extracted_skills,
                    jd_text
                )
                logging.info(f"✅ Match: {fit_score}% | Matching: {len(matching_skills)} | Missing: {len(missing_skills)}")
                logging.info(f"   Matching skills: {matching_skills}")
                logging.info(f"   Missing skills: {missing_skills[:5]}")
            except Exception as match_error:
                logging.error(f"❌ Matching failed: {match_error}", exc_info=True)
                return JsonResponse({
                    "success": False,
                    "message": "Failed to analyze job match. Please try again."
                })
            
            # ✅ VALIDATE WE GOT MEANINGFUL RESULTS
            if not matching_skills and not missing_skills:
                logging.warning("Both skills lists empty - JD may not contain tech requirements")
                # Show user's skills but indicate low match
                matching_skills = []
                missing_skills = []
                fit_score = 20.0
            
            # Calculate experience match
            experience_match = calculate_experience_match(resume, jd_text)
            
            # Calculate education match
            education_match = calculate_education_match(resume, jd_text)
            
            # Get learning resources for missing skills (only if we have missing skills)
            learning_resources = []
            if missing_skills:
                try:
                    learning_resources = get_learning_resources_with_gemini(missing_skills[:5])
                    logging.info(f"✅ Generated {len(learning_resources)} learning resource groups")
                except Exception as lr_error:
                    logging.error(f"Learning resources failed: {lr_error}")
                    learning_resources = _generate_fallback_resources(missing_skills[:5])

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


def _generate_fallback_resources(skills: List[str]) -> List[Dict]:
    """Generate basic learning resources as fallback"""
    resources = []
    for skill in skills:
        resources.append({
            "skill": skill,
            "resources": [
                {
                    "title": f"Learn {skill} on YouTube",
                    "url": f"https://www.youtube.com/results?search_query={skill.replace(' ', '+')}+tutorial",
                    "type": "Video",
                    "description": f"Free video tutorials on {skill}",
                    "duration": "Varies"
                },
                {
                    "title": f"{skill} on freeCodeCamp",
                    "url": f"https://www.freecodecamp.org/news/search/?query={skill.replace(' ', '%20')}",
                    "type": "Article",
                    "description": f"Free articles and guides",
                    "duration": "Self-paced"
                }
            ]
        })
    return resources

@csrf_exempt
def cover_letter_view(request):
    """Cover letter generation view with proper model handling"""
    if request.method == 'GET':
        # ✅ Get resume from session
        resume = None
        resume_id = request.session.get('resume_id')
        if resume_id:
            resume = Resume.objects.filter(id=resume_id).first()
        
        # Fetch recommended jobs based on resume skills if available
        recommended_jobs = []
        if resume and resume.extracted_skills:
            try:
                recommended_jobs = fetch_jobs_for_skills(
                    resume.extracted_skills[:10],
                    location="Remote",
                    max_results=10
                )
                logger.info(f"Loaded {len(recommended_jobs)} jobs for cover letter page")
            except Exception as e:
                logger.error(f"Error fetching jobs: {e}")
                # Fallback to generic jobs
                recommended_jobs = fetch_jobs_for_skills(
                    ["Software Developer"], 
                    location="Remote", 
                    max_results=10
                )
        else:
            # No resume, fetch generic jobs
            try:
                recommended_jobs = fetch_jobs_for_skills(
                    ["Software Developer"], 
                    location="Remote", 
                    max_results=10
                )
            except Exception as e:
                logger.error(f"Error fetching generic jobs: {e}")
                recommended_jobs = []
        
        # ✅ Pass resume data to template
        context = {
            'resume': resume,
            'has_resume': resume is not None,
            'recommended_jobs': recommended_jobs
        }
        
        return render(request, 'core/cover_letter.html', context)
    
    elif request.method == 'POST':
        try:
            job_title = request.POST.get('job_title', '').strip()
            company = request.POST.get('company', '').strip()
            jd_text = request.POST.get('job_description', '').strip()
            custom_prompt = request.POST.get('custom_prompt', '').strip()
            
            logger.info(f"Cover letter request - Title: '{job_title}', Company: '{company}', JD length: {len(jd_text)}")
            
            # Get resume from session
            resume_id = request.session.get('resume_id')
            logger.info(f"Session resume_id: {resume_id}")
            
            if not resume_id:
                return JsonResponse({
                    'success': False,
                    'error': 'No resume found. Please upload a resume first.'
                }, status=400)
            
            try:
                resume = Resume.objects.get(id=resume_id)
            except Resume.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Resume not found. Please upload again.'
                }, status=404)
            
            # Validate inputs
            if not jd_text:
                return JsonResponse({
                    'success': False,
                    'error': 'Job description is required'
                }, status=400)
            
            # Create or get JobDescription record
            job_description, created = JobDescription.objects.get_or_create(
                title=job_title or "Untitled Position",
                company=company or "Company",
                description=jd_text[:5000],
                defaults={
                    'location': 'Not specified',
                    'job_type': 'full-time',
                    'salary_range': '',
                    'required_skills': [],
                    'preferred_skills': [],
                }
            )
            
            if created:
                logger.info(f"✅ Created new JobDescription: {job_description.id}")
            else:
                logger.info(f"✅ Using existing JobDescription: {job_description.id}")
            
            # Generate cover letter with AI
            resume_text = resume.parsed_text or ""
            
            cover_letter_text = generate_cover_letter_with_gemini(
                resume_text=resume_text,
                jd_text=jd_text,
                custom_prompt=custom_prompt,
                applicant_name=resume.name or "",
                applicant_email=resume.email or "",
                job_title=job_title,
                company_name=company
            )
            
            logger.info(f"✅ Cover letter generated successfully ({len(cover_letter_text)} chars)")
            
            # Save to database
            cover_letter = CoverLetter.objects.create(
                resume=resume,
                job_description=job_description,
                content=cover_letter_text,
                custom_prompt=custom_prompt
            )
            
            logger.info(f"✅ Cover letter saved to database: {cover_letter.id}")
            
            return JsonResponse({
                'success': True,
                'cover_letter': cover_letter_text,
                'cover_letter_id': cover_letter.id
            })
            
        except ValidationError as e:
            error_msg = e.messages[0] if hasattr(e, 'messages') else str(e)
            logger.error(f"Cover letter validation error: {error_msg}")
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=400)
            
        except Exception as e:
            logger.error(f"Cover letter generation failed: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': f'Failed to generate cover letter: {str(e)}'
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

@csrf_exempt
def offer_analysis_view(request):
    """Offer letter analysis view"""
    if request.method == 'GET':
        return render(request, 'core/offer_analysis.html')
    
    elif request.method == 'POST':
        try:
            # Handle file upload
            offer_file = request.FILES.get('offer_file')
            offer_text = request.POST.get('offer_text', '').strip()
            
            if not offer_file and not offer_text:
                return JsonResponse({
                    'success': False,
                    'error': 'Please upload an offer letter or paste the text'
                }, status=400)
            
            # Extract text from file if provided
            if offer_file:
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(offer_file.name)[-1]) as temp_file:
                    for chunk in offer_file.chunks():
                        temp_file.write(chunk)
                    temp_file_path = temp_file.name
                
                try:
                    offer_text = extract_text_from_file(temp_file_path)
                finally:
                    try:
                        os.remove(temp_file_path)
                    except:
                        pass
            
            if not offer_text:
                return JsonResponse({
                    'success': False,
                    'error': 'Could not extract text from the offer letter'
                }, status=400)
            
            # Analyze offer letter with AI
            analysis = analyze_offer_letter_with_gemini(offer_text)
            
            # Save to database
            offer_letter = OfferLetter.objects.create(
                user=None,  # Anonymous
                file=offer_file if offer_file else None,
                text=offer_text,
                explanation=analysis.get('explanation', ''),
                risk_flags=analysis.get('risk_flags', []),
                ctc=analysis.get('ctc', ''),
                probation_period=analysis.get('probation_period', ''),
                notice_period=analysis.get('notice_period', '')
            )
            
            logging.info(f"✅ Offer letter analyzed and saved: {offer_letter.id}")
            
            return JsonResponse({
                'success': True,
                'analysis': {
                    'explanation': analysis.get('explanation', ''),
                    'ctc': analysis.get('ctc', 'Not specified'),
                    'probation_period': analysis.get('probation_period', 'Not specified'),
                    'notice_period': analysis.get('notice_period', 'Not specified'),
                    'risk_flags': analysis.get('risk_flags', []),
                    'key_points': analysis.get('key_points', [])
                },
                'offer_id': offer_letter.id
            })
            
        except Exception as e:
            logging.error(f"Offer analysis failed: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': f'Failed to analyze offer: {str(e)}'
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


# Helper functions for job matching
def calculate_experience_match(resume, jd_text):
    """Calculate experience match percentage"""
    try:
        experience_years = 0
        if resume.experience:
            # Extract years from experience entries
            for exp in resume.experience:
                years_match = re.search(r'(\d+)\+?\s*(?:years?|yrs?)', str(exp), re.IGNORECASE)
                if years_match:
                    experience_years = max(experience_years, int(years_match.group(1)))
        
        # Check JD for required years
        required_years = 0
        years_match = re.search(r'(\d+)\+?\s*(?:years?|yrs?)', jd_text, re.IGNORECASE)
        if years_match:
            required_years = int(years_match.group(1))
        
        if required_years == 0:
            return 75  # Default if no requirement specified
        
        if experience_years >= required_years:
            return 100
        elif experience_years >= required_years * 0.7:
            return 80
        elif experience_years >= required_years * 0.5:
            return 60
        else:
            return 40
            
    except Exception as e:
        logging.error(f"Experience match calculation failed: {e}", exc_info=True)  # ✅ Add exc_info
        return 70  # Default


def calculate_education_match(resume, jd_text):
    """Calculate education match percentage"""
    try:
        if not resume.education:
            return 50  # Default if no education info
        
        education_str = ' '.join(str(e).lower() for e in resume.education)
        jd_lower = jd_text.lower();
        
        # Check for degree requirements
        degree_keywords = ['bachelor', 'master', 'phd', 'b.tech', 'm.tech', 'mba', 'bca', 'mca']
        has_degree = any(keyword in education_str for keyword in degree_keywords)
        requires_degree = any(keyword in jd_lower for keyword in degree_keywords)
        
        if requires_degree and has_degree:
            return 100
        elif requires_degree and not has_degree:
            return 50
        elif has_degree:
            return 90
        else:
            return 70
            
    except Exception as e:
        logging.error(f"Education match calculation failed: {e}")
        return 70  # Default