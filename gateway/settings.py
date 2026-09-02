"""Django 设置。Agent 数据仍走 data/ 的 SQLAlchemy，不用 Django ORM。"""

from pathlib import Path

from config import ROOT_DIR, settings as app

BASE_DIR = ROOT_DIR
SECRET_KEY = app.django_secret_key
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
APPEND_SLASH = False

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "rest_framework",
    "gateway.apps.GatewayConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "gateway.middleware.DisableCSRFForAPI",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]

ROOT_URLCONF = "gateway.urls"
WSGI_APPLICATION = "gateway.wsgi.application"
ASGI_APPLICATION = "gateway.asgi.application"

# 占位：Django 要 DATABASES，真正的会话/记忆/RAG 不走这套
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": Path(ROOT_DIR) / ".django-unused.sqlite3",
    }
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    }
]

CLIENT_DIR = ROOT_DIR / "clients" / "web"
STATIC_URL = "/static/"
STATICFILES_DIRS = [CLIENT_DIR]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "UNAUTHENTICATED_USER": None,
}

USE_TZ = True
TIME_ZONE = "Asia/Shanghai"
LANGUAGE_CODE = "zh-hans"
