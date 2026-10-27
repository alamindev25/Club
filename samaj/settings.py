import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = os.environ.get("DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
ALLOWED_HOSTS.append(".onrender.com")

CSRF_TRUSTED_ORIGINS = [o for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o]
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")
CSRF_TRUSTED_ORIGINS.append("https://*.onrender.com")

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "rest_framework", "rest_framework.authtoken", "core",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "samaj.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages"]},
}]
WSGI_APPLICATION = "samaj.wsgi.application"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
LANGUAGE_CODE = "bn"
TIME_ZONE = "Asia/Dhaka"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.TokenAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAdminUser"],  # deny by default
    "DEFAULT_THROTTLE_RATES": {"login": "10/min", "payment": "20/hour"},
}
if not DEBUG:
    SECURE_SSL_REDIRECT = os.environ.get("SSL_REDIRECT", "1") == "1"
    SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ==============================================================
# SSLCOMMERZ PAYMENT GATEWAY CONFIGURATION
# ==============================================================
# লাইভ বা স্যান্ডবক্স ক্রেডেনশিয়াল এখানে অথবা environment variable-এ বসাবেন:
SSLCZ_STORE_ID = os.environ.get("SSLCZ_STORE_ID", "")
SSLCZ_STORE_PASSWD = os.environ.get("SSLCZ_STORE_PASSWD", "")
SSLCZ_IS_SANDBOX = os.environ.get("SSLCZ_IS_SANDBOX", "1") == "1"  # True হলে টেস্ট/স্যান্ডবক্স, False হলে লাইভ

# SSLCommerz API Endpoints
if SSLCZ_IS_SANDBOX:
    SSLCZ_SESSION_API = "https://sandbox.sslcommerz.com/gwprocess/v4/api.php"
    SSLCZ_VALIDATION_API = "https://sandbox.sslcommerz.com/validator/api/validationserverAPI.php"
else:
    SSLCZ_SESSION_API = "https://securepay.sslcommerz.com/gwprocess/v4/api.php"
    SSLCZ_VALIDATION_API = "https://securepay.sslcommerz.com/validator/api/validationserverAPI.php"
