# vercel_app.py

# This file is used by Vercel to deploy the application

import os
import sys

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set the Django settings module to use Vercel-specific settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cuteblog.vercel_settings')

# Import Django's WSGI handler
from django.core.wsgi import get_wsgi_application

# This is needed for Vercel deployment
application = get_wsgi_application()
app = application
