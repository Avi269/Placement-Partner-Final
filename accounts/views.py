"""
============================================================================
ACCOUNTS VIEWS - User Authentication & Profile Management
============================================================================
This module handles user registration, login, logout, and profile management.

Views:
- RegisterView (API): REST API endpoint for user registration
- UserProfileViewSet (API): Manage user profiles via API
- RegisterPage: Web interface for registration
- LoginPage: Web interface for login
- logout_view: Handle user logout

Features:
- JWT authentication for API
- Session authentication for web interface
- User profile creation with job tracking
- Secure password hashing
============================================================================
"""

# Django REST Framework imports
from rest_framework import generics, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated

# Django core imports
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django import forms
from django.views import View

# Local imports
from .serializers import RegisterSerializer, UserSerializer, UserProfileSerializer
from .models import UserProfile

# Get the User model (supports custom user models)
User = get_user_model()

# ============================================================================
# API VIEWS (REST API Endpoints)
# ============================================================================

class RegisterView(generics.CreateAPIView):
    """
    API endpoint for user registration
    
    POST /api/accounts/register/
    
    Body: {
        "email": "user@example.com",
        "password": "securepassword",
        "first_name": "John",
        "last_name": "Doe"
    }
    
    Returns: User data with auth token
    """
    queryset = User.objects.all()
    permission_classes = [AllowAny]  # Allow unauthenticated access
    serializer_class = RegisterSerializer

class UserProfileViewSet(viewsets.ModelViewSet):
    """
    API endpoints for user profile management
    
    GET /api/user-profile/ - Get current user's profile
    POST /api/user-profile/ - Create profile
    PUT/PATCH /api/user-profile/{id}/ - Update profile
    
    Tracks:
    - Total applications submitted
    - Interviews attended
    - Offers received
    - Calculated readiness score
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]  # Require login

    def get_queryset(self):
        """Only return the logged-in user's profile"""
        return UserProfile.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Automatically link profile to logged-in user"""
        serializer.save(user=self.request.user)

# ============================================================================
# WEB INTERFACE VIEWS (Django Templates)
# ============================================================================

class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "password"]


class RegisterPage(View):
    def get(self, request):
        form = RegisterForm()
        return render(request, "accounts/register.html", {"form": form})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()
            messages.success(request, "Account created successfully. Please log in.")
            return redirect("login-page")
        return render(request, "accounts/register.html", {"form": form})


class LoginPage(View):
    def get(self, request):
        form = AuthenticationForm()
        return render(request, "accounts/login.html", {"form": form})

    def post(self, request):
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name}!")
            return redirect("home")
        return render(request, "accounts/login.html", {"form": form})


class LogoutPage(View):
    def get(self, request):
        logout(request)
        messages.info(request, "You have been logged out.")
        return redirect("login-page")