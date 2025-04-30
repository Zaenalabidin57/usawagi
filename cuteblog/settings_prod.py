import os
from pathlib import Path
from dotenv import load_dotenv
import logging
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
try:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-qj2na8&2@zzf&q@t$wwum)vqjdq6d8xh^)+6n+wh4uyo2kc_y_')
    if SECRET_KEY == 'django-insecure-qj2na8&2@zzf&q@t$wwum)vqjdq6d8xh^)+6n+wh4uyo2kc_y_':
        logger.warning('Using insecure default SECRET_KEY. Set the SECRET_KEY environment variable in production.')
except Exception as e:
    logger.error(f"Failed to get SECRET_KEY: {e}")

# SECURITY WARNING: don't run with debug turned on in production!
try:
    DEBUG = os.environ.get('DEBUG', 'False') == 'True'
except Exception as e:
    logger.error(f"Failed to get DEBUG: {e}")

# Add Vercel URL to allowed hosts
try:
    ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,usawagi.vercel.app').split(',')
except Exception as e:
    logger.error(f"Failed to get ALLOWED_HOSTS: {e}")

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'blog',
    'shortlink',
    'whitenoise.runserver_nostatic',  # Add whitenoise for static files
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Add whitenoise middleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'cuteblog.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'cuteblog.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Media files
MEDIA_URL = os.environ.get('MEDIA_URL', 'https://your-media-server.com/media/')

# For local development, you can still use local media files
# But in production, media files will be served from the external server
if DEBUG:
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
else:
    # In production, we don't need a media root as files will be on the external server
    # This is just a placeholder directory for the file upload handling
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media_temp')

# Storage configuration
DEFAULT_FILE_STORAGE = 'blog.storage.SelectiveStorage'

# AWS S3 or compatible storage settings (for production)
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', '')
AWS_S3_ENDPOINT_URL = os.environ.get('AWS_S3_ENDPOINT_URL', '') # For DigitalOcean Spaces or other S3-compatible services
AWS_S3_CUSTOM_DOMAIN = os.environ.get('AWS_S3_CUSTOM_DOMAIN', '') # Your CDN domain if using one
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}
AWS_DEFAULT_ACL = 'public-read'
AWS_LOCATION = 'media'

# Whitenoise configuration
WHITENOISE_USE_FINDERS = True
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Security settings
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0  # Disabled for local development
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Only enable these in actual production environment
if os.environ.get('ENVIRONMENT') == 'production':
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
