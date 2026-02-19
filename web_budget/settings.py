from django.utils.translation import gettext_lazy as _
from pathlib import Path
import environ
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse_lazy
import os



# mimetypes.add_type("text/css", ".css", True)
root = environ.Path(__file__) - 3  # get root of the project
public_root = root.path('public/')
env = environ.Env()
environ.Env.read_env()  # reading .env file

DEBUG = env.bool('DEBUG', default=False)
TEMPLATE_DEBUG = DEBUG

SITE_ROOT = root()
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_ROOT = public_root('static')
STATIC_URL = env.str('STATIC_URL', default='/static/')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Build paths inside the project like this: BASE_DIR / 'subdir'.
LOGIN_URL = reverse_lazy('budgetdb:login')
LOGOUT_REDIRECT_URL = reverse_lazy('budgetdb:home')


SECRET_KEY = env.str('SECRET_KEY')

ALLOWED_HOSTS = [
    env.str('APP_HOST1', default='localhost'),
    env.str('APP_HOST2', default='127.0.0.1'),
]

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1','172.18.0.17'])

# Application definition

INSTALLED_APPS = [
    # 'django_addanother',
    'budgetdb.apps.BudgetdbConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'crispy_forms',
    "crispy_bootstrap5",
    'django.contrib.humanize',
    'django_extensions',
    'rest_framework',
    # 'debug_toolbar',
    'chartjs',
    'bootstrap_modal_forms',
    # 'dal',
    # 'dal_select2',
    'django_tables2',
    'django_filters',
    'django_select2',
]

AUTH_USER_MODEL = 'budgetdb.User'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = 'bootstrap5'
DJANGO_TABLES2_TEMPLATE = 'django_tables2/bootstrap5.html'
CSRF_TRUSTED_ORIGINS = ['http://code-server.patatemagique.biz',
                        'https://code-server.patatemagique.biz',
                        'http://code-server.patatemagique.biz:880',
                        'https://budget.patatemagique.biz',
                        ]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware', 
    'django.middleware.locale.LocaleMiddleware',           
    'django.middleware.common.CommonMiddleware',           
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware', 
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'crum.CurrentRequestUserMiddleware',                   
]

ROOT_URLCONF = 'web_budget.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'budgetdb.context_processors.theme_processor',
                'budgetdb.context_processors.version_info',
            ],
        },
    },
]

WSGI_APPLICATION = 'web_budget.wsgi.application'

# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env.str('DB_NAME'),
        'USER': env.str('DB_USER'),
        'PASSWORD': env.str('DB_PASSWORD'),
        'HOST': env.str('DB_HOST'),
        'PORT': env.str('DB_PORT'),
    }
}

# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        "OPTIONS": {
            "min_length": 9,
        },
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

INTERNAL_IPS = [
    # ...
    '192.168.1.11',
    '192.168.1.133',
    '192.168.1.228',
    # ...
]

# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/
LANGUAGES = (
    ('en-ca', _('English')),
    ('fr-ca', _('Francais')),
)

LANGUAGE_CODE = 'en-CA'

TIME_ZONE = 'America/Montreal'

USE_I18N = True

USE_TZ = False

EMAIL_BACKEND = env.str('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = env.str('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_USE_SSL = env.bool('EMAIL_USE_SSL', default=False)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_HOST_USER = env.str('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env.str('EMAIL_HOST_PASSWORD')

# Versioning
BUILD_DATE = os.getenv('APP_BUILD_DATE', 'Local Dev')
GIT_SHA = os.getenv('APP_GIT_SHA', 'Head')[:7]  # Shorten the hash
APP_VERSION = os.getenv('APP_VERSION', 'Dev-Local')
GITHUB_REPO_URL = "https://github.com/mathieugfortin/budgetdb"