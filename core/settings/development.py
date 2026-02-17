"""
Development settings - uses SQLite for local development
"""
from .common import *

INSTALLED_APPS += ['debug_toolbar']

DEBUG = True

# Security key for development only
SECRET_KEY = 'django-insecure-dev-key-for-local-testing-only-change-in-production'

# SQLite for local development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

INTERNAL_IPS = ['127.0.0.1']

def show_toolbar(request):
    return True

DEBUG_TOOLBAR_CONFIG = {"SHOW_TOOLBAR_CALLBACK": show_toolbar}

# Add debug toolbar middleware
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
