import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

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


IS_VERCEL = _env("VERCEL", "").lower() in ("1", "true", "yes")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = _env("DJANGO_SECRET_KEY", "")

# SECURITY WARNING: enable debug mode only for local development.
DEBUG = False if IS_VERCEL else _env("DJANGO_DEBUG", "True").lower() in (
    "1",
    "true",
    "yes",
)

_configured_hosts = [
    host.strip()
    for host in _env("DJANGO_ALLOWED_HOSTS", "").split(",")
    if host.strip()
]
_vercel_hosts = [
    _env(name).strip()
    for name in ("VERCEL_URL", "VERCEL_PROJECT_PRODUCTION_URL")
    if _env(name).strip()
]
ALLOWED_HOSTS = _configured_hosts or _vercel_hosts

if not DEBUG and not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY is required when DJANGO_DEBUG=False.")

if not DEBUG and not ALLOWED_HOSTS:
    raise RuntimeError("DJANGO_ALLOWED_HOSTS is required when DJANGO_DEBUG=False.")

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in _env("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
if IS_VERCEL and not CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS = [
        "https://" + host.removeprefix("https://").removeprefix("http://").rstrip("/")
        for host in _vercel_hosts
    ]


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

DATABASE_URL = _env("DATABASE_URL")
if DATABASE_URL:
    parsed_database_url = urlparse(DATABASE_URL)
    if parsed_database_url.scheme not in ("postgres", "postgresql"):
        raise ValueError("DATABASE_URL must use the postgres or postgresql scheme.")

    DB_OPTIONS = {
        key: values[-1]
        for key, values in parse_qs(parsed_database_url.query).items()
    }
    if not DEBUG:
        DB_OPTIONS.setdefault("sslmode", _env("DB_SSLMODE", "require"))

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote(parsed_database_url.path.lstrip("/")),
            "USER": unquote(parsed_database_url.username or ""),
            "PASSWORD": unquote(parsed_database_url.password or ""),
            "HOST": parsed_database_url.hostname or "",
            "PORT": str(parsed_database_url.port or "5432"),
            "OPTIONS": DB_OPTIONS,
        }
    }
else:
    DB_SSLMODE = _env("DB_SSLMODE", "require" if not DEBUG else "")
    DB_OPTIONS = {"sslmode": DB_SSLMODE} if DB_SSLMODE else {}

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": _env("DB_NAME", "touch_and_solve_db"),
            "USER": _env("DB_USER", "postgres"),
            "PASSWORD": _env("DB_PASSWORD", ""),
            "HOST": _env("DB_HOST", "localhost"),
            "PORT": _env("DB_PORT", "5432"),
            "OPTIONS": DB_OPTIONS,
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

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static"

# Supabase Storage is an S3-compatible service. It is enabled only when the
# deployment variables are present, keeping local development on the filesystem.
USE_SUPABASE_STORAGE = _env("USE_SUPABASE_STORAGE", "False").lower() in (
    "1",
    "true",
    "yes",
)

if USE_SUPABASE_STORAGE:
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
    AWS_ACCESS_KEY_ID = _env("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = _env("AWS_SECRET_ACCESS_KEY", "")
    AWS_STORAGE_BUCKET_NAME = _env("AWS_STORAGE_BUCKET_NAME", "")
    AWS_S3_REGION_NAME = _env("AWS_S3_REGION_NAME", "us-east-1")
    AWS_S3_ENDPOINT_URL = _env("AWS_S3_ENDPOINT_URL", "")
    AWS_S3_SIGNATURE_VERSION = _env("AWS_S3_SIGNATURE_VERSION", "aws4")
    AWS_S3_ADDRESSING_STYLE = _env("AWS_S3_ADDRESSING_STYLE", "path")
    AWS_S3_FILE_OVERWRITE = _env("AWS_S3_FILE_OVERWRITE", "False").lower() in (
        "1",
        "true",
        "yes",
    )
    AWS_S3_USE_SSL = _env("AWS_S3_USE_SSL", "True").lower() in (
        "1",
        "true",
        "yes",
    )
else:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


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

# Production security settings for Vercel and Supabase deployments.
SECURE_SSL_REDIRECT = _env(
    "SECURE_SSL_REDIRECT", "True" if IS_VERCEL else "False"
).lower() in (
    "1",
    "true",
    "yes",
)
SESSION_COOKIE_SECURE = _env(
    "SESSION_COOKIE_SECURE", "True" if IS_VERCEL else "False"
).lower() in (
    "1",
    "true",
    "yes",
)
CSRF_COOKIE_SECURE = _env(
    "CSRF_COOKIE_SECURE", "True" if IS_VERCEL else "False"
).lower() in (
    "1",
    "true",
    "yes",
)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = int(
    _env("SECURE_HSTS_SECONDS", "31536000" if IS_VERCEL else "0")
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
