"""Configurações por ambiente, lidas de variáveis de ambiente (.env)."""
import os
import re
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "sim"}


def _digits(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


class Config:
    # Segurança
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
    WTF_CSRF_TIME_LIMIT = 60 * 60 * 2  # 2 horas
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE", False)
    MAX_CONTENT_LENGTH = 64 * 1024  # formulários pequenos; bloqueia payloads abusivos
    TRUST_PROXY = _bool("TRUST_PROXY", False)

    # Dados do negócio (somente informações confirmadas)
    SITE_NAME = "Jaqueline Sias Despachante"
    SITE_URL = (os.getenv("SITE_URL") or "http://localhost:8000").rstrip("/")
    WHATSAPP_NUMBER = _digits(os.getenv("WHATSAPP_NUMBER"))
    WHATSAPP_DEFAULT_MESSAGE = os.getenv(
        "WHATSAPP_DEFAULT_MESSAGE",
        "Olá, Jaqueline! Acessei seu site e gostaria de informações sobre serviços de despachante.",
    )
    CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "").strip()
    INSTAGRAM_URL = os.getenv(
        "INSTAGRAM_URL", "https://www.instagram.com/jaquelinesiasdespachante/"
    ).strip()
    INSTAGRAM_HANDLE = os.getenv("INSTAGRAM_HANDLE", "@jaquelinesiasdespachante").strip()
    BUSINESS_CITY = os.getenv("BUSINESS_CITY", "").strip()  # ex.: Niterói
    BUSINESS_STATE = os.getenv("BUSINESS_STATE", "").strip()  # ex.: RJ
    BUSINESS_ADDRESS = os.getenv("BUSINESS_ADDRESS", "").strip()  # rua, número, bairro
    BUSINESS_POSTAL_CODE = os.getenv("BUSINESS_POSTAL_CODE", "").strip()
    BUSINESS_HOURS = os.getenv("BUSINESS_HOURS", "").strip()  # ex.: Seg a sex, 9h às 18h
    MAPS_EMBED_URL = os.getenv("MAPS_EMBED_URL", "").strip()  # https://www.google.com/maps/embed?pb=...
    GOOGLE_REVIEWS_URL = os.getenv("GOOGLE_REVIEWS_URL", "").strip()
    GOOGLE_SITE_VERIFICATION = os.getenv("GOOGLE_SITE_VERIFICATION", "").strip()

    # Formulário de contato
    CONTACT_STORAGE_PATH = os.getenv(
        "CONTACT_STORAGE_PATH", str(BASE_DIR / "instance" / "contatos.jsonl")
    )
    CONTACT_STORE_ENABLED = _bool("CONTACT_STORE_ENABLED", True)
    MAIL_SERVER = os.getenv("MAIL_SERVER", "").strip()
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587") or 587)
    MAIL_USE_TLS = _bool("MAIL_USE_TLS", True)
    MAIL_USE_SSL = _bool("MAIL_USE_SSL", False)
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "").strip()
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_SENDER = os.getenv("MAIL_SENDER", "").strip()
    MAIL_RECIPIENT = os.getenv("MAIL_RECIPIENT", "").strip()

    # Limite de requisições (Flask-Limiter). Use redis://... com múltiplos workers/instâncias.
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "300 per hour")
    RATELIMIT_CONTACT = os.getenv("RATELIMIT_CONTACT", "5 per minute;20 per day")
    RATELIMIT_HEADERS_ENABLED = True

    # Estáticos
    SEND_FILE_MAX_AGE_DEFAULT = 60 * 60 * 24 * 365  # URLs versionadas por hash

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

    DEBUG = False
    TESTING = False


class DevelopmentConfig(Config):
    DEBUG = True
    SEND_FILE_MAX_AGE_DEFAULT = 0
    TEMPLATES_AUTO_RELOAD = True


class ProductionConfig(Config):
    SESSION_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE", True)
    TRUST_PROXY = _bool("TRUST_PROXY", True)


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret"
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    CONTACT_STORE_ENABLED = False
    MAIL_SERVER = ""
    SITE_URL = "https://www.exemplo.com.br"
    WHATSAPP_NUMBER = "5521972602420"
    CONTACT_EMAIL = "contato@exemplo.com.br"
    BUSINESS_CITY = "Niterói"
    BUSINESS_STATE = "RJ"


CONFIGS = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config(name: str | None = None):
    name = (name or os.getenv("APP_ENV") or os.getenv("FLASK_ENV") or "production").lower()
    return CONFIGS.get(name, ProductionConfig)
