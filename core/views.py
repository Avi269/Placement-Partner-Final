from rest_framework import status, viewsets, generics
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from django.conf import settings
import os

from .models import Resume, JobDescription, CoverLetter, OfferLetter, SkillGapReport, UserProfile
from .serializers import (
    ResumeSerializer, JobDescriptionSerializer, CoverLetterSerializer,
    OfferLetterSerializer, SkillGapReportSerializer, UserProfileSerializer,
    ResumeUploadSerializer, JobMatchSerializer, CoverLetterGenerateSerializer,
    OfferLetterAnalyzeSerializer, ATSOptimizeSerializer
)
from .utils import (
    parse_resume_file, mock_generate_cover_letter, mock_analyze_offer_letter,
    mock_calculate_job_fit, mock_get_learning_resources, optimize_resume_for_ats,
    calculate_user_readiness_score, extract_skills_from_text
)

class ResumeViewSet(viewsets.ModelViewSet):
    queryset = Resume.objects.all()
    serializer_class = ResumeSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    @action(detail=False, methods=['post'])
    def upload(self, request):
        """Upload and parse resume"""
        serializer = ResumeUploadSerializer(data=request.data)
        if serializer.is_valid():
            resume = serializer.save()
            
            # Parse the uploaded file if provided
            if resume.file:
                file_path = resume.file.path
                parsed_data = parse_resume_file(file_path)
                
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

class JobDescriptionViewSet(viewsets.ModelViewSet):
    queryset = JobDescription.objects.all()
    serializer_class = JobDescriptionSerializer

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
            cover_letter_text = mock_generate_cover_letter(
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
            offer_letter = serializer.save()
            
            # Extract text from file or use provided text
            offer_text = offer_letter.text or ""
            if offer_letter.file:
                from .utils import extract_text_from_file
                offer_text = extract_text_from_file(offer_letter.file.path)
            
            # Analyze offer letter using AI
            analysis = mock_analyze_offer_letter(offer_text)
            
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
            fit_score, missing_skills, matching_skills = mock_calculate_job_fit(
                resume.extracted_skills, 
                jd.required_skills + jd.preferred_skills
            )
            
            # Get learning resources for missing skills
            suggested_resources = mock_get_learning_resources(missing_skills)
            
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

class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer

    @action(detail=False, methods=['get'])
    def profile(self, request):
        """Get user profile and readiness score"""
        user_id = request.query_params.get('user_id')
        
        if user_id:
            try:
                user_profile = UserProfile.objects.get(user_id=user_id)
                # Calculate readiness score
                readiness_score = calculate_user_readiness_score(user_profile)
                user_profile.readiness_score = readiness_score
                user_profile.save()
                
                return Response({
                    'user': user_profile.user.username,
                    'readiness_score': readiness_score,
                    'total_applications': user_profile.total_applications,
                    'interviews_attended': user_profile.interviews_attended,
                    'offers_received': user_profile.offers_received
                })
            except UserProfile.DoesNotExist:
                return Response({'error': 'User profile not found'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)

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

def resume_upload_view(request):
    """Resume upload page view"""
    return render(request, 'core/resume_upload.html')

def job_matching_view(request):
    """Job matching page view"""
    return render(request, 'core/job_matching.html')

def cover_letter_view(request):
    """Cover letter generation page view"""
    return render(request, 'core/cover_letter.html')

def offer_analysis_view(request):
    """Offer analysis page view"""
    return render(request, 'core/offer_analysis.html')

def dashboard(request):
    """Dashboard view"""
    return render(request, 'core/dashboard.html')

def profile(request):
    """User profile view"""
    return render(request, 'core/profile.html')
