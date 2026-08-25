"""
Development settings for AI CMS project.

Extends base settings with development-specific configuration.
"""

from .base import *

# Development settings override base
DEBUG = True
ALLOWED_HOSTS = ["*"]

# Development email backend - outputs to console
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Enable debug toolbar in development
INSTALLED_APPS += [
    "debug_toolbar",
]

MIDDLEWARE += [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

INTERNAL_IPS = [
    "127.0.0.1",
]

# Use local, optional settings if they exist
try:
    from .local import *
except ImportError:
    pass
