import os
from .common import *

DEBUG = False

SECRET_KEY = os.environ('SECRET_KEY')


ALLOWED_HOSTS = ["bayan-learningcenter.com", "www.bayan-learningcenter.com"]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'schooldb',
        'USER': 'schooluser',
        'PASSWORD': 'root@admin',
        'HOST': 'localhost',  
        'PORT': '3306',
    }
}



# Email Configuration for SMTP (Using Gmail)
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587 
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "ugacloud1@gmail.com"  
EMAIL_HOST_PASSWORD = "ghpjuehpwanwycci" 
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER