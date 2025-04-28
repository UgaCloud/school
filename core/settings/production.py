import os
from .common import *
import pymysql
pymysql.install_as_MySQLdb()

DEBUG = False

SECRET_KEY = os.environ['SECRET_KEY']


ALLOWED_HOSTS = ["bayan-learningcenter.com", "www.bayan-learningcenter.com"]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'schooldb',
#         'USER': 'schooluser',
#         'PASSWORD': 'root@admin',
#         'HOST': 'localhost',
#         'PORT': '5432',
#     }
# }

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'bayezieu_schooldb',
        'USER': 'bayezieu_bayan_user',
        'PASSWORD': '@bayan%dbuser',
        'HOST': '127.0.0.1',  
        'PORT': '3306',
    }
}




# Email Configuration for SMTP (Using Gmail)
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587 
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "wmizaac@gmail.com"
EMAIL_HOST_PASSWORD = "xxxqcmbgthxzvbuj" 
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER


STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
