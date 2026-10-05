import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env_file(env_path):
    """Minimal .env loader (no external dependency)."""
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_env_file(BASE_DIR / ".env")


def _env(key, default=""):
    return os.environ.get(key, default)


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = _env(
    "DJANGO_SECRET_KEY",
    "",
)

# SECURITY WARNING: 
DEBUG = _env("DJANGO_DEBUG", "True").lower() in ("1", "true", "yes")

ALLOWED_HOSTS = [h.strip() for h in _env("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'fms',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'fms.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'fms.context_processors.navbar_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'fms.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': _env('DB_NAME', 'touch_and_solve_db'),
        'USER': _env('DB_USER', 'postgres'),
        'PASSWORD': _env('DB_PASSWORD', ''),
        'HOST': _env('DB_HOST', 'localhost'),
        'PORT': _env('DB_PORT', '5432'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

# Enable timezone support
USE_TZ = True

# Set local timezone
TIME_ZONE = "Asia/Dhaka"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'


# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --------------------------
# Payment Gateway Configuration (SSLCommerz)
# --------------------------
SSL_COMMERZ_STORE_ID = _env("SSL_COMMERZ_STORE_ID", "")
SSL_COMMERZ_STORE_PASSWORD = _env("SSL_COMMERZ_STORE_PASSWORD", "")
SSLCOMMERZ_API_URL = _env(
    "SSLCOMMERZ_API_URL",
    "https://sandbox.sslcommerz.com/gwprocess/v4/api.php",
)

# Email Configuration
EMAIL_BACKEND = _env(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = _env("DEFAULT_FROM_EMAIL", "noreply@touchandsolve.com")

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
