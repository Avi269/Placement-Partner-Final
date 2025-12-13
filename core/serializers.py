"""
============================================================================
CORE SERIALIZERS
============================================================================
Django REST Framework serializers for converting models to/from JSON.
"""

from rest_framework import serializers
from .models import Resume, JobDescription, CoverLetter, OfferLetter, SkillGapReport

# ============================================================================
# MAIN MODEL SERIALIZERS
# ============================================================================

class ResumeSerializer(serializers.ModelSerializer):
    """Serializer for Resume model - Anonymous uploads only"""
    
    class Meta:
        model = Resume
        fields = '__all__'
        read_only_fields = ['parsed_text', 'extracted_skills', 'education', 'experience', 'name', 'email', 'phone', 'user']

class JobDescriptionSerializer(serializers.ModelSerializer):
    """Serializer for JobDescription model"""
    
    class Meta:
        model = JobDescription
        fields = '__all__'
        read_only_fields = ['user']

class CoverLetterSerializer(serializers.ModelSerializer):
    """Serializer for CoverLetter model with nested relationships"""
    resume = ResumeSerializer(read_only=True)
    job_description = JobDescriptionSerializer(read_only=True)
    
    class Meta:
        model = CoverLetter
        fields = '__all__'

class OfferLetterSerializer(serializers.ModelSerializer):
    """Serializer for OfferLetter model"""
    
    class Meta:
        model = OfferLetter
        fields = '__all__'
        read_only_fields = ['explanation', 'risk_flags', 'ctc', 'probation_period', 'notice_period', 'user']

class SkillGapReportSerializer(serializers.ModelSerializer):
    """Serializer for SkillGapReport model"""
    resume = ResumeSerializer(read_only=True)
    job_description = JobDescriptionSerializer(read_only=True)
    
    class Meta:
        model = SkillGapReport
        fields = '__all__'
        read_only_fields = ['fit_score', 'missing_skills', 'matching_skills', 'suggested_resources']

# ============================================================================
# SPECIAL-PURPOSE SERIALIZERS
# ============================================================================

class ResumeUploadSerializer(serializers.ModelSerializer):
    """Serializer for resume upload endpoint"""
    class Meta:
        model = Resume
        fields = ['file', 'parsed_text', 'name', 'email', 'phone', 'extracted_skills', 'education', 'experience']
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
    """Serializer for job matching endpoint"""
    resume_id = serializers.IntegerField(help_text="ID of resume to match")
    job_description_id = serializers.IntegerField(help_text="ID of job to match against")

class CoverLetterGenerateSerializer(serializers.Serializer):
    """Serializer for cover letter generation endpoint"""
    resume_id = serializers.IntegerField(help_text="ID of resume to use")
    job_description_id = serializers.IntegerField(help_text="ID of job being applied to")
    custom_prompt = serializers.CharField(required=False, allow_blank=True, help_text="Optional custom instructions for AI")

class OfferLetterAnalyzeSerializer(serializers.ModelSerializer):
    """Serializer for offer letter analysis endpoint"""
    class Meta:
        model = OfferLetter
        fields = ['file', 'text']
        extra_kwargs = {
            'file': {'required': False},
            'text': {'required': False},
        }

class ATSOptimizeSerializer(serializers.Serializer):
    """Serializer for ATS resume optimization endpoint"""
    resume_id = serializers.IntegerField(help_text="ID of resume to optimize")
    job_description_id = serializers.IntegerField(required=False, help_text="Optional job ID to optimize for")