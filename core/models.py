# Django ORM imports for database models
from django.db import models
from django.conf import settings
import uuid
import os

# ============================================================================
# FILE UPLOAD PATH GENERATORS
# ============================================================================
# These functions generate unique file paths for uploaded files to prevent
# filename collisions and organize uploads in specific directories

def resume_file_path(instance, filename):
    """Generate unique file path for resume uploads using UUID
    
    Args:
        instance: The model instance being saved
        filename: Original uploaded filename
    
    Returns:
        str: Path like 'resumes/uuid.ext'
    """
    # Extract file extension from original filename
    ext = filename.split('.')[-1]
    # Generate unique filename using UUID to prevent conflicts
    filename = f"{uuid.uuid4()}.{ext}"
    # Return full path: media/resumes/uuid.ext
    return os.path.join('resumes', filename)

def offer_letter_file_path(instance, filename):
    """Generate unique file path for offer letter uploads using UUID
    
    Args:
        instance: The model instance being saved
        filename: Original uploaded filename
    
    Returns:
        str: Path like 'offer_letters/uuid.ext'
    """
    # Extract file extension from original filename
    ext = filename.split('.')[-1]
    # Generate unique filename using UUID
    filename = f"{uuid.uuid4()}.{ext}"
    # Return full path: media/offer_letters/uuid.ext
    return os.path.join('offer_letters', filename)

# ============================================================================
# RESUME MODEL
# ============================================================================
# Stores parsed resume data including skills, education, and experience

class Resume(models.Model):
    """Model for storing parsed resume information and extracted data
    
    Supports both file uploads (PDF/DOCX/TXT) and direct text paste. 
    Uses AI (Gemini) to parse resumes and extract structured information.
    """
    
    # Owner of this resume (optional - supports anonymous uploads)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,  # Delete resume if user is deleted
        null=True,  # Allow null for anonymous uploads
        blank=True,
        help_text="User who uploaded this resume"
    )
    
    # Uploaded resume file (stored in media/resumes/)
    file = models.FileField(
        upload_to=resume_file_path,  # Use custom path generator
        null=True, 
        blank=True,
        help_text="Uploaded resume file (PDF/DOCX/TXT)"
    )
    
    # Complete text content extracted from resume
    parsed_text = models.TextField(
        blank=True,
        help_text="Full text extracted from resume for processing"
    )
    
    # JSON array of extracted technical and professional skills
    extracted_skills = models.JSONField(
        default=list,  # Default to empty list
        blank=True,
        help_text="Skills extracted from resume (e.g., ['Python', 'Django', 'SQL'])"
    )
    
    # JSON array of educational qualifications
    education = models.JSONField(
        default=list,
        blank=True,
        help_text="Education history with degrees, institutions, and years"
    )
    
    # JSON array of work experience entries
    experience = models.JSONField(
        default=list,
        blank=True,
        help_text="Work history with companies, positions, and durations"
    )
    
    # Applicant's personal information extracted from resume
    name = models.CharField(
        max_length=255, 
        blank=True,
        help_text="Candidate's full name"
    )
    email = models.EmailField(
        blank=True,
        help_text="Candidate's email address"
    )
    phone = models.CharField(
        max_length=20, 
        blank=True,
        help_text="Candidate's phone number"
    )
    
    # Automatic timestamp tracking
    created_at = models.DateTimeField(
        auto_now_add=True,  # Set only on creation
        help_text="When this resume was uploaded"
    )
    updated_at = models.DateTimeField(
        auto_now=True,  # Update on every save
        help_text="When this resume was last modified"
    )

    def __str__(self):
        """Return human-readable representation"""
        return f"Resume - {self.name or 'Unknown'}"
    
    class Meta:
        ordering = ['-created_at']  # Show newest first
        verbose_name = "Resume"
        verbose_name_plural = "Resumes"

# ============================================================================
# JOB DESCRIPTION MODEL
# ============================================================================
# Stores job posting details for matching with resumes

class JobDescription(models.Model):
    """Model for storing job descriptions and requirements"""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        help_text="User who created this job description"
    )
    
    title = models.CharField(
        max_length=255,
        help_text="Job title or position name"
    )
    
    company = models.CharField(
        max_length=255, 
        blank=True,
        help_text="Company or organization name"
    )
    
    # ✅ CHANGE 'text' to 'description' to match views.py usage
    description = models.TextField(
        help_text="Full job description including responsibilities and requirements"
    )
    
    # ✅ ADD MISSING FIELDS
    location = models.CharField(
        max_length=255,
        blank=True,
        default='Not specified',
        help_text="Job location"
    )
    
    job_type = models.CharField(
        max_length=50,
        blank=True,
        default='full-time',
        help_text="Employment type (full-time, part-time, contract)"
    )
    
    salary_range = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text="Salary range"
    )
    
    required_skills = models.JSONField(
        default=list,
        blank=True,
        help_text="Mandatory skills required"
    )
    
    preferred_skills = models.JSONField(
        default=list, 
        blank=True,
        help_text="Nice-to-have skills"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this job description was created"
    )

    def __str__(self):
        return f"{self.title} at {self.company}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Job Description"
        verbose_name_plural = "Job Descriptions"

# ============================================================================
# COVER LETTER MODEL
# ============================================================================
# Stores AI-generated cover letters tailored to specific job applications

class CoverLetter(models.Model):
    """Model for storing AI-generated cover letters"""
    
    resume = models.ForeignKey(
        Resume, 
        on_delete=models.CASCADE,
        help_text="Resume this cover letter is based on"
    )
    
    job_description = models.ForeignKey(
        JobDescription, 
        on_delete=models.SET_NULL,
        null=True,  # ✅ Make it optional
        blank=True,
        help_text="Job description this cover letter is for"
    )
    
    content = models.TextField(
        default='',  # ✅ Add default value
        blank=True,  # ✅ Allow blank in forms
        help_text="Generated cover letter content"
    )
    
    custom_prompt = models.TextField(
        blank=True, 
        null=True,
        help_text="Custom instructions provided by user"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this cover letter was generated"
    )

    def __str__(self):
        job_title = self.job_description.title if self.job_description else "Unknown Position"
        return f"Cover Letter for {self.resume.name} - {job_title}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Cover Letter"
        verbose_name_plural = "Cover Letters"

# ============================================================================
# OFFER LETTER MODEL
# ============================================================================
# Stores offer letter analysis including key terms and risk assessment

class OfferLetter(models.Model):
    """Model for storing and analyzing job offer letters
    
    Analyzes offer letters using AI to extract key terms (CTC, notice period,
    probation), identify red flags, and provide negotiation advice.
    """
    
    # User analyzing this offer
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        help_text="User who uploaded this offer letter"
    )
    
    # Uploaded offer letter file
    file = models.FileField(
        upload_to=offer_letter_file_path, 
        null=True, 
        blank=True,
        help_text="Uploaded offer letter file (PDF/DOCX)"
    )
    
    # Offer letter text (extracted from file or pasted)
    text = models.TextField(
        blank=True,
        help_text="Full text content of the offer letter"
    )
    
    # AI-generated comprehensive analysis
    explanation = models.TextField(
        blank=True,
        help_text="Detailed AI analysis explaining the offer terms"
    )
    
    # List of concerning terms or red flags
    risk_flags = models.JSONField(
        default=list, 
        blank=True,
        help_text="Problematic clauses or concerning terms found"
    )
    
    # Key terms extracted from offer
    ctc = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Cost to Company - total annual compensation"
    )
    probation_period = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Duration of probation period"
    )
    notice_period = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Required notice period for resignation"
    )
    
    # Creation timestamp
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this offer was analyzed"
    )

    def __str__(self):
        """Return representation with creation date"""
        return f"Offer Letter Analysis - {self.created_at.strftime('%Y-%m-%d')}"
    
    class Meta:
        ordering = ['-created_at']  # Newest first
        verbose_name = "Offer Letter"
        verbose_name_plural = "Offer Letters"

# ============================================================================
# SKILL GAP REPORT MODEL
# ============================================================================
# Stores job matching analysis, skill gaps, and learning recommendations

class SkillGapReport(models.Model):
    """Model for storing skill gap analysis and job fit scores
    
    Compares resume skills with job requirements to calculate fit percentage,
    identify missing skills, and recommend learning resources.
    """
    
    # Resume being analyzed
    resume = models.ForeignKey(
        Resume, 
        on_delete=models.CASCADE,
        help_text="Resume being matched against job"
    )
    
    # Job being matched
    job_description = models.ForeignKey(
        JobDescription, 
        on_delete=models.CASCADE,
        help_text="Job description for skill comparison"
    )
    
    # Calculated job fit percentage (0.00 to 100.00)
    fit_score = models.DecimalField(
        max_digits=5,  # Max: 100.00
        decimal_places=2,  # Two decimal places
        default=0.0,
        help_text="Percentage match between resume and job (0-100)"
    )
    
    # Skills that are required but not present in resume
    missing_skills = models.JSONField(
        default=list, 
        blank=True,
        help_text="Skills required by job but missing from resume"
    )
    
    # Skills present in both resume and job requirements
    matching_skills = models.JSONField(
        default=list, 
        blank=True,
        help_text="Skills that match between resume and job"
    )
    
    # Learning recommendations for missing skills
    suggested_resources = models.JSONField(
        default=list, 
        blank=True,
        help_text="Recommended courses or resources to learn missing skills"
    )
    
    # Creation timestamp
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this analysis was performed"
    )

    def __str__(self):
        """Return representation with fit score"""
        return f"Skill Gap Report - {self.fit_score}% fit"
    
    class Meta:
        ordering = ['-created_at']  # Newest first
        verbose_name = "Skill Gap Report"
        verbose_name_plural = "Skill Gap Reports"

# ============================================================================
# LEARNING RESOURCE MODEL
# ============================================================================
# Stores learning resources for skills

class LearningResource(models.Model):
    """Model for storing learning resources for skills"""
    skill = models.CharField(max_length=100, db_index=True)
    title = models.CharField(max_length=255)
    url = models.URLField()
    resource_type = models.CharField(
        max_length=50,
        choices=[
            ('tutorial', 'Tutorial'),
            ('course', 'Course'),
            ('book', 'Book'),
            ('docs', 'Documentation'),
            ('video', 'Video'),
            ('certification', 'Certification'),
            ('guide', 'Guide')
        ]
    )
    description = models.TextField()
    duration = models.CharField(max_length=50, help_text="e.g., '10-15 hours'")
    priority = models.IntegerField(default=0, help_text="Higher priority resources shown first")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-priority', 'skill', 'title']
        indexes = [
            models.Index(fields=['skill', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.skill} - {self.title}"

