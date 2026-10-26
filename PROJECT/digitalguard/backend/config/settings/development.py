"""
DigitalGuard Django Settings — Development
Inherits from base.py. Enables debug features.
"""

from .base import *  # noqa: F401, F403

DEBUG = True

INSTALLED_APPS += [  # noqa: F405
    # Dev tools (optional)
]

# Relaxed security for local development
CORS_ALLOW_ALL_ORIGINS = True

# Show all SQL queries in development
# Uncomment to enable:
# LOGGING['loggers']['django.db.backends'] = {
#     'handlers': ['console'],
#     'level': 'DEBUG',
# }
