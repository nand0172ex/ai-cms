"""
Production settings for AI CMS project.

Extends base settings with production-specific security and performance settings.
"""

from .base import *

# Production security settings
DEBUG = False

# Use ManifestStaticFilesStorage for cache busting
STORAGES["staticfiles"][
    "BACKEND"
] = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

# Security settings
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_SECURITY_POLICY = {
    "default-src": ("'self'",),
    "script-src": ("'self'",),
    "style-src": ("'self'", "'unsafe-inline'"),
}

# HTTPS/SSL settings (enable in production)
# SECURE_SSL_REDIRECT = True
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
# SECURE_HSTS_SECONDS = 31536000
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True

# Email configuration (override with environment variables)
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# Optional local production settings override
try:
    from .local import *
except ImportError:
    pass
