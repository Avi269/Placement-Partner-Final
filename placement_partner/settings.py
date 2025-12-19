"""
============================================================================
DJANGO SETTINGS - Placement Partner Application
============================================================================
Configuration file for the Placement Partner Django application.

Key Configurations:
- Database: SQLite (development) - easily switchable to PostgreSQL
- Authentication: JWT tokens + session auth
- File Uploads: Media files stored in media/ directory
- Static Files: CSS, JS, images in static/ directory
- APIs: REST Framework with CORS enabled
- AI Integration: Google Gemini API for resume/job analysis

Environment Variables (set in .env file):
- SECRET_KEY: Django secret key for security
- DEBUG: Enable debug mode (True/False)
- ALLOWED_HOSTS: Comma-separated list of allowed hosts
- GEMINI_API_KEY: Google Gemini API key for AI features
- DATABASE_URL: Database connection (optional)

Installed Apps:
- core: Main placement partner features
- accounts: User authentication and profiles
- rest_framework: REST API framework
- corsheaders: Cross-Origin Resource Sharing

For production deployment:
1. Set DEBUG=False
2. Configure ALLOWED_HOSTS
3. Use PostgreSQL database
4. Set up proper SECRET_KEY
5. Configure static files serving (WhiteNoise/nginx)
============================================================================
"""

import os
from pathlib import Path
from decouple import config  # ✅ Add this import

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# BASE_DIR points to the project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================================
# ENVIRONMENT VARIABLES - Load from .env
# ============================================================================

# Security
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

# Gemini AI Configuration
GEMINI_API_KEY = config('GEMINI_API_KEY')
GEMINI_MODEL = config('GEMINI_MODEL', default='gemini-2.0-flash-exp')

# Job Search APIs
ADZUNA_APP_ID = config('ADZUNA_APP_ID', default='')
ADZUNA_API_KEY = config('ADZUNA_API_KEY', default='')
RAPIDAPI_KEY = config('RAPIDAPI_KEY', default='')
JSEARCH_API_KEY = config('JSEARCH_API_KEY', default='')

# Email Configuration
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

# Cache Settings
CACHE_TIMEOUT = config('CACHE_TIMEOUT', default=3600, cast=int)

# Logging
LOG_LEVEL = config('LOG_LEVEL', default='INFO')
LOG_FILE = config('LOG_FILE', default='logs/app.log')

# Feature Flags
ENABLE_AI_RESUME_PARSING = config('ENABLE_AI_RESUME_PARSING', default=True, cast=bool)
ENABLE_JOB_RECOMMENDATIONS = config('ENABLE_JOB_RECOMMENDATIONS', default=True, cast=bool)
ENABLE_COVER_LETTER_GENERATION = config('ENABLE_COVER_LETTER_GENERATION', default=True, cast=bool)
ENABLE_OFFER_ANALYSIS = config('ENABLE_OFFER_ANALYSIS', default=True, cast=bool)

# ============================================================================
# DJANGO SETTINGS (rest of your existing settings)
# ============================================================================

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'core',
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "placement_partner.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "placement_partner.wsgi.application"

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Use PostgreSQL in production
if os.getenv('DATABASE_URL'):
    import dj_database_url
    DATABASES['default'] = dj_database_url.parse(os.getenv('DATABASE_URL'))


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = "static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# Production static files
if not DEBUG:
    STATIC_ROOT = BASE_DIR / 'staticfiles'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Media files configuration
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Security settings
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = 'DENY'

# CORS settings
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000').split(',')
CORS_ALLOW_CREDENTIALS = True

# File upload settings
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_FILE_TYPES = ['pdf', 'docx', 'doc', 'txt']

# Session settings
SESSION_COOKIE_AGE = 86400  # 24 hours in seconds
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

# Logging configuration
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',  # Force UTF-8
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# Create logs directory if it doesn't exist
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}
