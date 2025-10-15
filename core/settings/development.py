from .common import *
import pymysql
pymysql.install_as_MySQLdb()


DEBUG = True

SECRET_KEY = 'django-insecure-gqgpv+7+nke4*fefzsr63+a=r0!!t@bgn!_1a*5(_^ow@^3t)('


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(BASE_DIR / 'db.sqlite3'),
    }
}



INTERNAL_IPS = [
    '127.0.0.1',
]

def show_toolbar(request):
    return True

DEBUG_TOOLBAR_CONFIG = {
  "SHOW_TOOLBAR_CALLBACK" : show_toolbar,
}