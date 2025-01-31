import os
from .common import *

DEBUG = False

SECRET_KEY = os.environ('SECRET_KEY')

ALLOWED_HOSTS = ['bayan-10a5ed283f94.herokuapp.com']


# Email Configuration for SMTP (Using Gmail)
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587 
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "wmizaac@gmail.com"  
EMAIL_HOST_PASSWORD = "ghpjuehpwanwycci" 
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER