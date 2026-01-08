from .base import *

DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "terradart-test",
        "TIMEOUT": None,
        "OPTIONS": {},
    }
}

AMADEUS_ENABLED = False
FOURSQUARE_ENABLED = False
LLM_SUMMARY_ENABLED = False

