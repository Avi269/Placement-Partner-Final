"""
============================================================================
ACCOUNTS MODELS - Custom User & Profile
============================================================================
Custom user model using email as the primary authentication field instead
of username. Includes user profile for tracking job application progress.

Models:
- CustomUser: User authentication model (email-based login)
- UserProfile: Extended profile with job search statistics

Features:
- Email-based authentication (no username required)
- User profile automatically created on user registration
- Track applications, interviews, offers
- Calculate job readiness score
============================================================================
"""

# Django authentication imports
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.base_user import BaseUserManager

# Django core imports
from django.db import models
from django.conf import settings

# Django signals for automatic profile creation
from django.db.models.signals import post_save
from django.dispatch import receiver

# ============================================================================
# CUSTOM USER MANAGER
# ============================================================================

class CustomUserManager(BaseUserManager):
    """
    Manager for CustomUser model
    Handles user creation with email instead of username
    """
    
    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a regular user with email and password
        
        Args:
            email: User's email address (required)
            password: User's password
            **extra_fields: Additional fields (first_name, last_name, etc.)
        
        Returns:
            CustomUser instance
        """
        if not email:
            raise ValueError("The Email field is required")
        
        # Normalize email (lowercase domain)
        email = self.normalize_email(email)
        
        # Create user instance
        user = self.model(email=email, **extra_fields)
        
        # Hash and set password
        user.set_password(password)
        
        # Save to database
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a superuser (admin) with email and password
        
        Args:
            email: Admin's email address
            password: Admin's password
            **extra_fields: Additional fields
        
        Returns:
            CustomUser instance with admin privileges
        """
        # Set admin flags
        extra_fields.setdefault('is_staff', True)  # Can access admin site
        extra_fields.setdefault('is_superuser', True)  # Has all permissions

        # Validate admin flags
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        # Create user with admin privileges
        return self.create_user(email, password, **extra_fields)

# ============================================================================
# CUSTOM USER MODEL
# ============================================================================

class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model with email-based authentication
    
    Uses email instead of username for login.
    Extends Django's AbstractBaseUser with email as the unique identifier.
    """
    
    # Set custom user manager
    objects = CustomUserManager()

    # === AUTHENTICATION CONFIGURATION ===
    # Use email for login instead of username
    USERNAME_FIELD = 'email'
    # Required fields when creating superuser (besides email and password)
    REQUIRED_FIELDS = ['first_name', 'last_name']

    # === USER FIELDS ===
    # Email is the unique identifier for authentication
    email = models.EmailField(
        max_length=254, 
        unique=True,
        help_text="User's email address (used for login)"
    )
    
    # Personal information
    first_name = models.CharField(
        max_length=50, 
        blank=True,
        help_text="User's first name"
    )
    last_name=models.CharField(max_length=50, blank=True)
    is_student=models.BooleanField(default=False)
    is_recruiter=models.BooleanField(default=False)
    date_joined=models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    def __str__(self):
        return self.email


class UserProfile(models.Model):
    user=models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    readiness_score=models.DecimalField(max_digits=5, decimal_places=1,blank=True,null=True)
    applications=models.IntegerField(null=True,blank=True)
    interviews=models.IntegerField(null=True,blank=True)
    offers=models.IntegerField(null=True, blank=True)
    profile_image=models.ImageField(upload_to="image/", blank=True, null=True) # need to adjust

    def __str__(self):
        return self.user.email


# @receiver(post_save, sender=CustomUser)
# def create_user_profile(sender, instance, created, **kwargs):
#     if created:
#         UserProfile.objects.create(user=instance)

@receiver(post_save, sender=CustomUser)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        try:
            instance.userprofile.save()
        except UserProfile.DoesNotExist:
            # Create profile if it doesn't exist
            UserProfile.objects.create(user=instance)
