import os
from .common import *

DEBUG = False

SECRET_KEY = os.environ('SECRET_KEY')

ALLOWED_HOSTS = ['bayan-10a5ed283f94.herokuapp.com']