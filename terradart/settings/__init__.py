import os
from importlib import import_module

ENV_MAP = {
    "dev": "dev",
    "development": "dev",
    "prod": "prod",
    "production": "prod",
}

DJANGO_ENV = os.getenv("DJANGO_ENV", "dev").lower()
module_name = ENV_MAP.get(DJANGO_ENV, "dev")

settings_module = f"{__name__}.{module_name}"
module = import_module(settings_module)

for attribute in dir(module):
    if attribute.isupper():
        globals()[attribute] = getattr(module, attribute)

