import os
from urllib.parse import urlparse, parse_qs

from django.core.exceptions import ImproperlyConfigured

from .base import *

if SECRET_KEY == "django-insecure-local":
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set in production")

DEBUG = False

ALLOWED_HOSTS = ["terradart.com", "www.terradart.com"]

CORS_ALLOWED_ORIGINS = ["https://terradart.com", "https://www.terradart.com"]

RAILWAY_DOMAIN = os.getenv("RAILWAY_PRIVATE_DOMAIN")
if RAILWAY_DOMAIN:
    ALLOWED_HOSTS = [*ALLOWED_HOSTS, RAILWAY_DOMAIN]
    CORS_ALLOWED_ORIGINS = [
        *CORS_ALLOWED_ORIGINS,
        f"https://{RAILWAY_DOMAIN}",
    ]

CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

DB_URL = os.getenv("DATABASE_URL")
if DB_URL:
    parsed = urlparse(DB_URL)
    query_params = parse_qs(parsed.query)
    sslmode = (query_params.get("sslmode") or ["require"])[0]
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": parsed.username,
            "PASSWORD": parsed.password,
            "HOST": parsed.hostname,
            "PORT": parsed.port or "5432",
            "OPTIONS": {"sslmode": sslmode},
        }
    }

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
