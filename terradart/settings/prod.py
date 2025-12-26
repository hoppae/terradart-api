from django.core.exceptions import ImproperlyConfigured

from .base import *

if SECRET_KEY == "django-insecure-local":
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set in production")

DEBUG = False

ALLOWED_HOSTS = ["terradart.com", "www.terradart.com"]

CORS_ALLOWED_ORIGINS = ["https://terradart.com", "https://www.terradart.com"]

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
