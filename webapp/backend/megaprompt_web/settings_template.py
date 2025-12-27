"""
Django settings for megaprompt_web project.

This is a template that should be merged into the generated settings.py
"""

# Add these to INSTALLED_APPS
INSTALLED_APPS_ADDITIONS = [
    "rest_framework",
    "corsheaders",
    "channels",
    "api",
    "core",
]

# Add these to MIDDLEWARE (at appropriate positions)
MIDDLEWARE_ADDITIONS = [
    "corsheaders.middleware.CorsMiddleware",  # Should be near the top
]

# REST Framework configuration
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",  # For local use only
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
}

# CORS settings (for local development)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

CORS_ALLOW_CREDENTIALS = True

# Channels configuration
ASGI_APPLICATION = "megaprompt_web.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",  # For local development
    },
}

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB

