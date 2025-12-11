"""
============================================================================
CORE SERIALIZERS
============================================================================
Django REST Framework serializers for converting models to/from JSON.

Serializers handle:
- Model to JSON conversion for API responses
- JSON to model conversion for API requests
- Data validation
- Nested relationships (e.g., resume with user info)
============================================================================
"""

from rest_framework import serializers
from .models import Resume, JobDescription, CoverLetter, OfferLetter, SkillGapReport
from accounts.serializers import UserSerializer

# ============================================================================
# MAIN MODEL SERIALIZERS
# ============================================================================
# These serializers handle the main CRUD operations for each model

class ResumeSerializer(serializers.ModelSerializer):
    """Serializer for Resume model with nested user information
    
    Includes full resume data with related user details.
    Used for GET requests to retrieve resume information.
    """
    # Include nested user data in response (read-only)
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Resume
        fields = '__all__'  # Include all fields from Resume model
        # Fields that are auto-generated and shouldn't be modified by users
        read_only_fields = ['parsed_text', 'extracted_skills', 'education', 'experience', 'name', 'email', 'phone']

class JobDescriptionSerializer(serializers.ModelSerializer):
    """Serializer for JobDescription model
    
    Handles job posting data including title, company, and requirements.
    Used for creating and retrieving job descriptions.
    """
    # Include user who created this job description
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = JobDescription
        fields = '__all__'  # All fields available for read/write

class CoverLetterSerializer(serializers.ModelSerializer):
    """Serializer for CoverLetter model with nested relationships
    
    Includes full resume and job description data along with generated letter.
    Used for retrieving cover letter details.
    """
    # Include nested resume and job description data
    resume = ResumeSerializer(read_only=True)
    job_description = JobDescriptionSerializer(read_only=True)
    
    class Meta:
        model = CoverLetter
        fields = '__all__'

class OfferLetterSerializer(serializers.ModelSerializer):
    """Serializer for OfferLetter model
    
    Handles offer letter data including analysis results.
    Analysis fields are read-only as they're AI-generated.
    """
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = OfferLetter
        fields = '__all__'
        # AI-generated fields that users cannot directly modify
        read_only_fields = ['explanation', 'risk_flags', 'ctc', 'probation_period', 'notice_period']

class SkillGapReportSerializer(serializers.ModelSerializer):
    """Serializer for SkillGapReport model
    
    Includes job matching results, skill gaps, and learning recommendations.
    All analysis fields are read-only as they're AI-generated.
    """
    # Include nested resume and job description
    resume = ResumeSerializer(read_only=True)
    job_description = JobDescriptionSerializer(read_only=True)
    
    class Meta:
        model = SkillGapReport
        fields = '__all__'
        # AI-generated analysis fields (read-only)
        read_only_fields = ['fit_score', 'missing_skills', 'matching_skills', 'suggested_resources']

# ============================================================================
# SPECIAL-PURPOSE SERIALIZERS
# ============================================================================
# These serializers handle specific API endpoint operations

class ResumeUploadSerializer(serializers.ModelSerializer):
    """Serializer for resume upload endpoint
    
    Accepts either a file upload or direct text paste.
    All fields are optional to support flexible input methods.
    """
    class Meta:
        model = Resume
        # Only include fields relevant for upload
        fields = ['file', 'parsed_text', 'name', 'email', 'phone', 'extracted_skills', 'education', 'experience']
        # Make all fields optional - user can provide file OR text
        extra_kwargs = {
            'file': {'required': False},
            'parsed_text': {'required': False},
            'name': {'required': False},
            'email': {'required': False},
            'phone': {'required': False},
            'extracted_skills': {'required': False},
            'education': {'required': False},
            'experience': {'required': False},
        }

class JobMatchSerializer(serializers.Serializer):
    """Serializer for job matching endpoint
    
    Accepts resume and job description IDs to perform skill gap analysis.
    Not tied to a model - just validates input IDs.
    """
    resume_id = serializers.IntegerField(help_text="ID of resume to match")
    job_description_id = serializers.IntegerField(help_text="ID of job to match against")

class CoverLetterGenerateSerializer(serializers.Serializer):
    """Serializer for cover letter generation endpoint
    
    Accepts resume ID, job ID, and optional custom instructions.
    """
    resume_id = serializers.IntegerField(help_text="ID of resume to use")
    job_description_id = serializers.IntegerField(help_text="ID of job being applied to")
    # Optional: custom instructions for AI (e.g., "emphasize leadership experience")
    custom_prompt = serializers.CharField(required=False, allow_blank=True, help_text="Optional custom instructions for AI")

class OfferLetterAnalyzeSerializer(serializers.ModelSerializer):
    """Serializer for offer letter analysis endpoint
    
    Accepts either a file upload or pasted text for analysis.
    Both fields are optional to support flexible input.
    """
    class Meta:
        model = OfferLetter
        fields = ['file', 'text']  # Only need file or text for analysis
        # Either field can be provided (not both required)
        extra_kwargs = {
            'file': {'required': False},
            'text': {'required': False},
        }

class ATSOptimizeSerializer(serializers.Serializer):
    """Serializer for ATS resume optimization endpoint
    
    Accepts resume ID and optionally a job description ID.
    Generates ATS-friendly version of resume.
    """
    resume_id = serializers.IntegerField(help_text="ID of resume to optimize")
    # Optional: target specific job for optimization
    job_description_id = serializers.IntegerField(required=False, help_text="Optional job ID to optimize for") 