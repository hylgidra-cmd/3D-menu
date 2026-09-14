import mimetypes
from pathlib import Path
from decouple import config
from datetime import datetime, timedelta
import dj_database_url

# Python's mimetypes module doesn't know these by default, so both get served
# as application/octet-stream - iOS Quick Look and some Android AR viewers
# key off the exact Content-Type to decide whether to launch AR at all.
mimetypes.add_type("model/gltf-binary", ".glb")
mimetypes.add_type("model/vnd.usdz+zip", ".usdz")

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
# localhost/127.0.0.1/backend are always allowed so the Docker healthcheck
# (hitting http://localhost:8000/health/ from inside the container) works
# regardless of what public domain is configured below.
ALLOWED_HOSTS = [h for h in config("ALLOWED_HOSTS", default="").split(",") if h] + [
    "localhost",
    "127.0.0.1",
    "backend",
]
if DEBUG:
    # LAN IP for phone testing on the dev machine's network, plus a
    # cloudflared quick tunnel (AR/camera needs HTTPS), which gets a random
    # *.trycloudflare.com hostname each run.
    ALLOWED_HOSTS.append("192.168.1.20")
    ALLOWED_HOSTS.append(".trycloudflare.com")

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]
THIRD_APPS = [
    "rest_framework",
    "corsheaders",
    "rest_framework_simplejwt.token_blacklist",
]
LOCAL_APPS = [
    "apps.user",
    "apps.restaurant",
    "apps.table",
    "apps.eat",
]
INSTALLED_APPS = DJANGO_APPS + THIRD_APPS + LOCAL_APPS

AUTH_USER_MODEL = "user.User"

FRONTEND_BASE_URL = config("FRONTEND_BASE_URL", default="http://localhost:3000")

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Platform3d.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'Platform3d.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases

DATABASES = {
    "default": dj_database_url.config(default=config("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"))
}

if DEBUG:
    # Local dev: keep uploaded files on disk, no Cloudflare credentials required.
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
else:
    CLOUDFLARE_ACCOUNT_ID = config("CLOUDFLARE_ACCOUNT_ID")

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

    AWS_ACCESS_KEY_ID = config("CLOUDFLARE_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = config("CLOUDFLARE_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = config("CLOUDFLARE_R2_BUCKET")
    AWS_S3_ENDPOINT_URL = f"https://{CLOUDFLARE_ACCOUNT_ID}.r2.cloudflarestorage.com"
    AWS_S3_CUSTOM_DOMAIN = config("CLOUDFLARE_R2_PUBLIC_URL").replace("https://", "")
    AWS_S3_REGION_NAME = "auto"
    AWS_DEFAULT_ACL = None
    AWS_S3_ADDRESSING_STYLE = "virtual"
    AWS_QUERYSTRING_AUTH = False  # чтобы публичные URL были без подписи


# Password validation
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny"
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle"
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "10/minute",
        "user": "100/minute"
    },
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer"
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser"
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.user.authentication.CookieJWTAuthentication"
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    # APIClient in tests defaults to multipart otherwise, which doesn't match
    # how the real frontends call these (JSON) and trips 415s on JSON-only views.
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

if DEBUG:
    # Local dev: three separate frontend apps hit this backend from the same
    # IP, and just loading a page (auth check + refresh + login) can burn
    # through several anonymous requests - 10/minute trips almost immediately
    # and locks out login with 429s until the window rolls over.
    REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["anon"] = "1000/minute"

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    # "UPDATE_LAST_LOGIN": False,
    #
    "ALGORITHM": "HS256",
    "SIGNING_KEY": config("SECRET_KEY"),
    # "VERIFYING_KEY": "",
    # "AUDIENCE": None,
    # "ISSUER": None,
    # "JSON_ENCODER": None,
    # "JWK_URL": None,
    # "LEEWAY": 0,
    #
    # "AUTH_HEADER_TYPES": ("Bearer",),
    # "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    # "USER_ID_FIELD": "id",
    # "USER_ID_CLAIM": "user_id",
    # "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",
    #
    # "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    # "TOKEN_TYPE_CLAIM": "token_type",
    # "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",
    #
    # "JTI_CLAIM": "jti",
    #
    # "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    # "SLIDING_TOKEN_LIFETIME": timedelta(minutes=5),
    # "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=1),
    #
    # "TOKEN_OBTAIN_SERIALIZER": "rest_framework_simplejwt.serializers.TokenObtainPairSerializer",
    # "TOKEN_REFRESH_SERIALIZER": "rest_framework_simplejwt.serializers.TokenRefreshSerializer",
    # "TOKEN_VERIFY_SERIALIZER": "rest_framework_simplejwt.serializers.TokenVerifySerializer",
    # "TOKEN_BLACKLIST_SERIALIZER": "rest_framework_simplejwt.serializers.TokenBlacklistSerializer",
    # "SLIDING_TOKEN_OBTAIN_SERIALIZER": "rest_framework_simplejwt.serializers.TokenObtainSlidingSerializer",
    # "SLIDING_TOKEN_REFRESH_SERIALIZER": "rest_framework_simplejwt.serializers.TokenRefreshSlidingSerializer",
    #
    # "CHECK_REVOKE_TOKEN": False,
    # "REVOKE_TOKEN_CLAIM": "hash_password",
    # "CHECK_USER_IS_ACTIVE": True,
}

# CORS_ALLOW_ALL_ORIGINS (wildcard) is incompatible with credentialed
# (cookie) requests, so an explicit origin allowlist is used in both modes.
CORS_ALLOW_CREDENTIALS = True
if DEBUG:
    CORS_ALLOWED_ORIGIN_REGEXES = [
        r"^http://localhost:\d+$",
        r"^http://127\.0\.0\.1:\d+$",
        # Any RFC1918 private LAN address, on any port - dev machine's LAN IP
        # can change (DHCP, switching to a phone hotspot, etc.).
        r"^http://192\.168\.\d{1,3}\.\d{1,3}:\d+$",
        r"^http://10\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+$",
        r"^http://172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}:\d+$",
        # cloudflared quick tunnel, used for phone testing over HTTPS.
        r"^https://[a-z0-9-]+\.trycloudflare\.com$",
    ]
else:
    CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS").split(",")

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

if not DEBUG:
    # Caddy terminates TLS and proxies to gunicorn over plain HTTP inside the
    # docker network - without this, Django can't tell the original request
    # was HTTPS and SECURE_SSL_REDIRECT loops forever.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    # The Docker healthcheck hits gunicorn directly over plain HTTP (bypassing
    # Caddy), so it never carries the X-Forwarded-Proto header - exempt it
    # from the redirect above or it 301s to an HTTPS port gunicorn can't serve.
    SECURE_REDIRECT_EXEMPT = [r"^health/$"]
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30  # 30 days
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}
