from pathlib import Path
from datetime import timedelta
from django.conf import settings
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = config("DJ_DEBUG", default=False, cast=bool)

SECRET_KEY = config("DJ_SECRET_KEY")

BASE_URL = config("DJ_BASE_URL")

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'


ADD_NEW_ORDER_KEY = config("ADD_NEW_ORDER_KEY")
WATER_LEVEL_KEY = config("WATER_LEVEL_KEY")
TEMPERATURE_KEY = config("TEMPERATURE_KEY")
PEOPLE_COUNT_KEY = config("PEOPLE_COUNT_KEY")
GUARD_DETECTION_KEY = config("GUARD_DETECTION_KEY")
GARBAGE_DETECTION_KEY = config("GARBAGE_DETECTION_KEY")
RECYCLE_DETECTION_KEY = config("RECYCLE_DETECTION_KEY", default="")
EMPTY_CHAIR_DETECTION_KEY = config("EMPTY_CHAIR_DETECTION_KEY", default="")
SECURITY_DETECTION_KEY = config("SECURITY_DETECTION_KEY", default="")
KITCHEN_CAMERA_KEY = config("KITCHEN_CAMERA_KEY")
AGGF_CAMERA_KEY = config("AGGF_CAMERA_KEY")
FACE_DETECTION_KEY = config("FACE_DETECTION_KEY")
GARBAGE_MONITORING_KEY = config("GARBAGE_MONITORING_KEY")
BUFFET_VIOLATION_KEY = config("BUFFET_VIOLATION_KEY")
BATHROOM_MONITORING_KEY = config("BATHROOM_MONITORING_KEY")
SENTIMENT_ANALYSIS_KEY = config("SENTIMENT_ANALYSIS_KEY")
CAMERA_SECRET_KEY = config("CAMERA_SECRET_X_KEY")
ROUTER_SECRET_KEY = config("ROUTER_SECRET_KEY")

TUYA_ACCESS_ID = config("TUYA_ACCESS_ID")
TUYA_ACCESS_KEY = config("TUYA_ACCESS_KEY")
TUYA_API_ENDPOINT = config("TUYA_API_ENDPOINT", default="https://openapi.tuyaeu.com")

ALLOWED_HOSTS = ["*"]
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:5176",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
    "http://127.0.0.1:5176",
    "http://54.82.50.121:8000",
    "https://hajj.transformsai.com",
    "https://hajjdrf.transformsai.com",
    "https://hajjc.transformsai.com",
    "https://hajjcdrf.transformsai.com",
    "https://backend.aihajjservices.com",
    "https://aihajjservices.com",
    "https://baitguests.com",
    "https://b2c.aihajjservices.com",
    "https://hajj.aiqualitysolutions.com",
    "https://dashboard.aiqualitysolutions.com",
    "https://technical-dashboard.aiqualitysolutions.com",
    "https://backend.outstandingknowledge.com",
    "https://dashboard.outstandingknowledge.com",
]

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:5176",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
    "http://127.0.0.1:5176",
    "http://54.82.50.121:8000",
    "https://hajj.transformsai.com",
    "https://hajjdrf.transformsai.com",
    "https://hajjc.transformsai.com",
    "https://hajjcdrf.transformsai.com",
    "https://backend.aihajjservices.com",
    "https://aihajjservices.com",
    "https://baitguests.com",
    "https://b2c.aihajjservices.com",
    "https://hajj.aiqualitysolutions.com",
    "https://dashboard.aiqualitysolutions.com",
    "https://technical-dashboard.aiqualitysolutions.com",
    "https://backend.outstandingknowledge.com",
    "https://dashboard.outstandingknowledge.com",
]

CORS_ALLOWED_ORIGIN_REGEXES = [
    "http://localhost:8000",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:5176",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
    "http://127.0.0.1:5176",
    "http://54.82.50.121:8000",
    "https://hajj.transformsai.com",
    "https://hajjdrf.transformsai.com",
    "https://hajjc.transformsai.com",
    "https://hajjcdrf.transformsai.com",
    "https://backend.aihajjservices.com",
    "https://aihajjservices.com",
    "https://baitguests.com",
    "https://b2c.aihajjservices.com",
    "https://hajj.aiqualitysolutions.com",
    "https://dashboard.aiqualitysolutions.com",
    "https://technical-dashboard.aiqualitysolutions.com",
    "https://dashboard.outstandingknowledge.com",
    "https://backend.outstandingknowledge.com",
]
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    # "ACCESS_TOKEN_LIFETIME": timedelta(seconds=10),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=2),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": settings.SECRET_KEY,
}

# Add this to your CORS configuration
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-secret-key',  # Add your custom header here
    'x-api-key',
]

# Application definition

INSTALLED_APPS = [
    "corsheaders",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    'drf_spectacular_sidecar',
    "django_celery_results",
    'django_celery_beat',
    'django_extensions',

    "authentication",
    "tent",
    "camera",
    "sensor",
    "weight",
    "livestream",
    'counter_camera',
    'technical_dashboard',
    'access_point',
    'model_retrainer',
    'tuya_proxy',
]

AUTH_USER_MODEL = "authentication.MyUser"

SPECTACULAR_SETTINGS = {
    'TITLE': 'Hajj Tent Api',
    'DESCRIPTION': 'Hajj Tent description',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SWAGGER_UI_DIST': 'SIDECAR',  # shorthand to use the sidecar instead
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'REDOC_DIST': 'SIDECAR',
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

MIDDLEWARE = [

    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

]

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        'rest_framework.authentication.SessionAuthentication',
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    # 'EXCEPTION_HANDLER': 'authentication.exceptions.custom_exception_handler',
    "DEFAULT_PAGINATION_CLASS": "utils.pagination.CustomPageNumberPagination",
    "PAGE_SIZE": 10,
}

ROOT_URLCONF = "hajjtent23DRF.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "hajjtent23DRF.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": config("DJ_DB_ENGINE"),
        "NAME": config("DJ_DB_NAME"),
        "USER": config("DJ_DB_USER"),
        "PASSWORD": config("DJ_DB_PASSWORD"),
        "HOST": config("DJ_DB_HOST"),
        "PORT": config("DJ_DB_PORT"),
    }
}

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "en-us"

# TIME_ZONE = "Asia/Dhaka"
# TIME_ZONE = "Asia/Riyadh"
TIME_ZONE = "Asia/Riyadh"

USE_I18N = True
USE_L10N = True

USE_TZ = True

STATICFILES_DIRS = [
    BASE_DIR / "static",
]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SESSION_COOKIE_AGE = 86400
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': 'error.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}

DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000000

CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TIMEZONE = "Asia/Riyadh"
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_RESULT_SERIALIZER = "json"
CELERY_TASK_SERIALIZER = "json"


# Prefix all metrics with your project name
# PROMETHEUS_METRIC_NAMESPACE = "aihajj"

# # Fine-grained latency buckets for API monitoring
# PROMETHEUS_LATENCY_BUCKETS = (
#     .005, .01, .025, .05, .075, .1, .25, .5, .75,
#     1.0, 2.5, 5.0, 7.5, 10.0, float("inf")
# )
# # Expose metrics on a separate port (not through nginx/gunicorn)
# PROMETHEUS_METRICS_EXPORT_PORT = 8001
# PROMETHEUS_METRICS_EXPORT_ADDRESS = '127.0.0.1'  # localhost only, never public
