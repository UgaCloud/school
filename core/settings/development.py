from .common import *


DEBUG = True

SECRET_KEY = 'django-insecure-gqgpv+7+nke4*fefzsr63+a=r0!!t@bgn!_1a*5(_^ow@^3t)('


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'schooldb',
        'USER': 'postgres',
        'PASSWORD': 'root',
        'HOST': 'localhost',  
        'PORT': '5432',
    }
}

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }
