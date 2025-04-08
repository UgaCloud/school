from .common import *


DEBUG = True

SECRET_KEY = 'django-insecure-gqgpv+7+nke4*fefzsr63+a=r0!!t@bgn!_1a*5(_^ow@^3t)('


# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'schooldb',
#         'USER': 'postgres',
#         'PASSWORD': 'root',
#         'HOST': '162.254.35.90',  
#         'PORT': '5432',
#     }
# }

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'schooldb',
        'USER': 'schooluser',
        'PASSWORD': 'root@admin',
        'HOST': '162.254.35.90',  
        'PORT': '3306',
    }
}

