# vercel_app.py

# This file is used by Vercel to deploy the application

import os
from cuteblog.wsgi import application

# This is needed for Vercel deployment
app = application
