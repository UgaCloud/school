from .common import *


DEBUG = True

SECRET_KEY = 'django-insecure-gqgpv+7+nke4*fefzsr63+a=r0!!t@bgn!_1a*5(_^ow@^3t)('




# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': 'schooldb',
#         'USER': 'schooluser',
#         'PASSWORD': 'root@admin',
#         'HOST': 'localhost',  
#         'PORT': '3306',
#     }
# }


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(BASE_DIR / 'db.sqlite3'),
    }
}
