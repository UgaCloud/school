"""
Django settings for core project.
"""
import os
from pathlib import Path
from decouple import config

import pymysql
pymysql.install_as_MySQLdb()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'crispy_forms',
    'crispy_bootstrap4',
    'widget_tweaks',
    'app',
    'secondary',
]

CRISPY_TEMPLATE_PACK = "bootstrap4"

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'app.middleware.request_user.RequestUserMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'app.middleware.update_jazzmin.UpdateJazzminMiddleware',
    'app.middleware.dynamic_jazzmin.DynamicJazzminMiddleware',
    'core.middleware.AutoLogoutMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'app.context_processors.school_settings'
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# Database - Define in development.py or production.py

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Kampala'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGOUT_REDIRECT_URL = 'login'

SESSION_COOKIE_AGE = 1800
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True

DEV_TUNNEL_URL = ""

# Software versioning
SOFTWARE_NAME = config("SOFTWARE_NAME", default="School MIS")
SOFTWARE_VERSION = config("SOFTWARE_VERSION", default="1.0.0")
SOFTWARE_RELEASE_CHANNEL = config("SOFTWARE_RELEASE_CHANNEL", default="stable")
SOFTWARE_BUILD = config("SOFTWARE_BUILD", default="")

# Backup monitoring configuration
BACKUP_ENABLED = config("BACKUP_ENABLED", default=False, cast=bool)
BACKUP_METHOD = config("BACKUP_METHOD", default="hybrid")
BACKUP_SCHEDULE = config("BACKUP_SCHEDULE", default="daily 02:00")
BACKUP_DIR = config("BACKUP_DIR", default=str(BASE_DIR / "backups"))
BACKUP_MAX_AGE_HOURS = config("BACKUP_MAX_AGE_HOURS", default=48, cast=int)
MYSQLDUMP_BIN = config("MYSQLDUMP_BIN", default="mysqldump")
PG_DUMP_BIN = config("PG_DUMP_BIN", default="pg_dump")
PSQL_BIN = config("PSQL_BIN", default="psql")

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = ""
EMAIL_PORT = 465
EMAIL_USE_SSL = True
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
DEFAULT_FROM_EMAIL = ""

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
        'file': {'class': 'logging.FileHandler', 'filename': 'general.log', 'formatter': 'verbose'}
    },
    'loggers': {
        '': {'handlers': ['console', 'file'], 'level': 'INFO'}
    },
    'formatters': {
        'verbose': {'format': '{asctime} ({levelname}) - {name} {message}', 'style': '{'}
    }
}

USER_ROLE_PREFIXES = {
    'Admin': 'Admin-',
    'Teacher': 'Teacher-',
    'Bursar': 'bursar-',
    'Director of studies': 'Dos-',
    'Head master': 'Hm-',
    'class Teacher': 'Class-Teacher-',
}

JAZZMIN_SETTINGS = {
    "site_title": "Bayan Learning Center Admin",
    "site_header": "Bayan Learning Center Administration",
    "site_brand": "Bayan Learning Center",
    "custom_css": "css/rainbow.css",
    "site_logo": "images/user.png",
    "site_logo_classes": "brand-image img-circle elevation-3",
    "site_icon": "images/favicon.ico",
    "welcome_sign": "Welcome to Bayan Learning Center Admin",
    "copyright": "UgaCloud 2025",
    "search_model": ["auth.User", "auth.Group"],
    "show_sidebar": True,
    "navigation_expanded": True,
    "topmenu_links": [
        {"name": "Dashboard", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"app": "app"},
        {"model": "auth.User"},
    ],
    "icons": {"auth": "fas fa-users-cog", "auth.user": "fas fa-user", "auth.group": "fas fa-users"},
    "related_modal_active": True,
    "changeform_format": "vertical_tabs",
    "language_chooser": False,
    "show_ui_builder": False,
    "recent_actions": {"icon": "fas fa-history", "title": "Recent Activities", "card_class": "card-primary"},
}

JAZZMIN_UI_TWEAKS = {
    "theme": "flatly",
    "dark_mode_theme": None,
    "theme_condition": "always",
    "navbar": "navbar-primary navbar-dark",
    "sidebar": "sidebar-dark-primary",
    "navbar_fixed": True,
    "sidebar_fixed": True,
    "footer_fixed": False,
    "actions_sticky_top": True,
    "button_classes": {
        "primary": "btn btn-primary",
        "secondary": "btn btn-outline-secondary",
        "info": "btn btn-info",
        "warning": "btn btn-warning",
        "danger": "btn btn-danger",
        "success": "btn btn-success",
    },
}
