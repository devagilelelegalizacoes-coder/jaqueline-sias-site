"""Fábrica da aplicação Flask — Jaqueline Sias Despachante."""
import hashlib
import logging
import mimetypes
import re
import sys
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv
from flask import Flask, request, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from markupsafe import Markup
from werkzeug.middleware.proxy_fix import ProxyFix

load_dotenv()
# alguns sistemas (ex.: Windows) não conhecem o tipo WebP; com nosniff a imagem não abriria
mimetypes.add_type("image/webp", ".webp")

from .config import get_config  # noqa: E402
from .settings_store import SettingsStore, get_settings, tracking_enabled  # noqa: E402

csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)


def _configure_logging(app: Flask) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(app.config["LOG_LEVEL"])
    logging.getLogger("werkzeug").setLevel(logging.WARNING)


def _register_template_helpers(app: Flask) -> None:
    static_dir = Path(app.static_folder)
    icons_dir = static_dir / "images" / "icons"

    @lru_cache(maxsize=None)
    def _file_hash(path: str) -> str:
        try:
            return hashlib.md5((static_dir / path).read_bytes(), usedforsecurity=False).hexdigest()[:10]
        except OSError:
            return "0"

    def asset(path: str, _external: bool = False) -> str:
        """URL de arquivo estático com versão por hash (cache longo e seguro)."""
        if app.debug:
            _file_hash.cache_clear()
        return url_for("static", filename=path, v=_file_hash(path), _external=_external)

    @lru_cache(maxsize=None)
    def _icon_svg(name: str) -> str:
        svg = (icons_dir / f"{name}.svg").read_text(encoding="utf-8")
        svg = re.sub(r"<!--.*?-->", "", svg, flags=re.S).strip()
        svg = re.sub(r"\s+", " ", svg)
        # remove width/height/class somente da tag <svg> raiz (não de <rect>, etc.)
        root_end = svg.index(">")
        root = re.sub(r'\s(width|height|class)="[^"]*"', "", svg[:root_end])
        return root + svg[root_end:]

    def icon(name: str, cls: str = "") -> Markup:
        svg = _icon_svg(name)
        attrs = f'class="{("icon icon-" + name + " " + cls).strip()}" aria-hidden="true" focusable="false"'
        return Markup(svg.replace("<svg", f"<svg {attrs}", 1))

    def wa_link(message: str | None = None) -> str | None:
        """Link wa.me com mensagem; None se o número não estiver configurado."""
        c = get_settings()["contato"]
        number = c["whatsapp"]
        if not number or len(number) < 12:
            return None
        text = message or c["whatsapp_mensagem"] or app.config["WHATSAPP_DEFAULT_MESSAGE"]
        return f"https://wa.me/{number}?text={quote(text, safe='')}"

    def phone_display() -> str | None:
        n = get_settings()["contato"]["whatsapp"]
        if n.startswith("55") and len(n) in (12, 13):
            local = n[2:]
            if len(local) == 11:
                return f"({local[:2]}) {local[2:7]}-{local[7:]}"
            return f"({local[:2]}) {local[2:6]}-{local[6:]}"
        return None

    def tel_href(display: str) -> str:
        digits = re.sub(r"\D", "", display or "")
        return "tel:+" + (digits if digits.startswith("55") and len(digits) >= 12 else "55" + digits)

    def location_label() -> str:
        c = get_settings()["contato"]
        return ", ".join(p for p in (c["cidade"], c["estado"]) if p)

    def media(ref: str, _external: bool = False) -> str:
        """URL de uma foto: enviada pelo painel (uploads/...) ou arquivo estático do site."""
        if ref.startswith(("http://", "https://")):
            return ref
        if ref.startswith("uploads/"):
            url = url_for("main.uploaded", filename=ref.removeprefix("uploads/"))
            return app.config["SITE_URL"] + url if _external else url
        if _external:
            return app.config["SITE_URL"] + url_for("static", filename=ref)
        return asset(ref)

    def paragraphs(text: str) -> list[str]:
        return [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]

    app.jinja_env.globals.update(
        asset=asset, icon=icon, wa_link=wa_link, phone_display=phone_display,
        location_label=location_label, media=media, paragraphs=paragraphs, tel_href=tel_href,
    )
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True

    @app.context_processor
    def inject_site():
        from datetime import date
        site = get_settings()
        return {
            "cfg": app.config,
            "site": site,
            "txt": site["textos"],
            "show": site["aparencia"]["secoes"],
            "has_tracking": tracking_enabled(site),
            "current_year": date.today().year,
        }


# Domínios liberados na CSP conforme as ferramentas configuradas no painel.
TRACKER_CSP = {
    "ga4": {
        "script": ["https://www.googletagmanager.com"],
        "connect": ["https://*.google-analytics.com", "https://*.analytics.google.com", "https://*.googletagmanager.com"],
        "img": ["https://*.google-analytics.com", "https://*.googletagmanager.com"],
    },
    "google_ads": {
        "script": ["https://www.googletagmanager.com", "https://www.googleadservices.com", "https://googleads.g.doubleclick.net"],
        "connect": ["https://www.google.com", "https://www.googleadservices.com", "https://googleads.g.doubleclick.net", "https://*.doubleclick.net"],
        "img": ["https://www.google.com", "https://www.google.com.br", "https://googleads.g.doubleclick.net", "https://www.googleadservices.com"],
        "frame": ["https://td.doubleclick.net", "https://www.googletagmanager.com"],
    },
    "meta": {
        "script": ["https://connect.facebook.net"],
        "connect": ["https://www.facebook.com", "https://connect.facebook.net"],
        "img": ["https://www.facebook.com"],
        "frame": ["https://www.facebook.com"],
    },
    "tiktok": {
        "script": ["https://analytics.tiktok.com"],
        "connect": ["https://analytics.tiktok.com", "https://*.tiktok.com", "https://*.tiktokw.us"],
        "img": ["https://analytics.tiktok.com"],
    },
    "clarity": {
        "script": ["https://www.clarity.ms", "https://*.clarity.ms"],
        "connect": ["https://*.clarity.ms", "https://c.bing.com"],
        "img": ["https://*.clarity.ms", "https://c.bing.com"],
    },
}


def build_csp(site: dict | None, admin: bool = False) -> str:
    src = {
        "script": ["'self'"], "style": ["'self'"], "img": ["'self'", "data:"], "connect": ["'self'"],
        "frame": [],
    }
    if admin:
        src["img"].append("blob:")
    elif site:
        if site["contato"]["mapa_url"]:
            src["frame"].append("https://www.google.com")
        p = site["pixels"]
        for key, domains in TRACKER_CSP.items():
            if p[key]:
                for kind, values in domains.items():
                    src[kind] += [v for v in values if v not in src[kind]]
        if p["gtm"] or p["codigo_head"] or p["codigo_body"]:
            # Tag Manager e código personalizado podem carregar qualquer script:
            # libera scripts inline e de origens https (menos restritivo).
            src["script"] += ["'unsafe-inline'", "https:"]
            src["style"] += ["'unsafe-inline'", "https:"]
            src["img"].append("https:")
            src["connect"].append("https:")
            src["frame"].append("https:")
    return "; ".join([
        "default-src 'self'",
        "script-src " + " ".join(src["script"]),
        "style-src " + " ".join(src["style"]),
        "img-src " + " ".join(src["img"]),
        "font-src 'self'",
        "connect-src " + " ".join(src["connect"]),
        "frame-src " + (" ".join(src["frame"]) or "'none'"),
        "form-action 'self'",
        "base-uri 'self'",
        "frame-ancestors 'none'",
        "object-src 'none'",
    ])


def _register_security_headers(app: Flask) -> None:
    @app.after_request
    def set_headers(resp):
        h = resp.headers
        if "Content-Security-Policy" not in h:
            admin = request.blueprint == "admin"
            site = None
            if resp.mimetype == "text/html" and not admin:
                try:
                    site = get_settings()
                except Exception:  # noqa: BLE001 - nunca derrubar a resposta por causa da CSP
                    app.logger.exception("Falha ao montar a CSP com as configurações do painel")
            h["Content-Security-Policy"] = build_csp(site, admin)
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("X-Frame-Options", "DENY")
        h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        h.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=(), interest-cohort=()")
        h.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        if app.config["SESSION_COOKIE_SECURE"]:
            h.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if resp.mimetype == "text/html":
            h.setdefault("Cache-Control", "no-cache")
        return resp


def _register_upload_limits(app: Flask) -> None:
    """O site aceita só formulários pequenos; o painel precisa receber fotos.
    Registrado antes do CSRF, que lê o formulário."""
    @app.before_request
    def admin_limits():
        if request.path.startswith("/admin"):
            request.max_content_length = app.config["ADMIN_MAX_CONTENT_LENGTH"]
            request.max_form_memory_size = 4 * 1024 * 1024


def create_app(config_name: str | None = None, overrides: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(get_config(config_name))
    if overrides:
        app.config.update(overrides)
    _configure_logging(app)

    if app.config["TRUST_PROXY"]:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    app.extensions["settings_store"] = SettingsStore(app.config["SETTINGS_PATH"])
    _register_upload_limits(app)
    csrf.init_app(app)
    app.config["RATELIMIT_DEFAULTS"] = [app.config["RATELIMIT_DEFAULT"]]
    limiter.init_app(app)

    _register_template_helpers(app)
    _register_security_headers(app)

    from .admin import bp as admin_bp
    from .routes import bp, register_error_handlers
    app.register_blueprint(bp)
    app.register_blueprint(admin_bp)
    register_error_handlers(app)

    if not app.config["WHATSAPP_NUMBER"]:
        app.logger.warning("WHATSAPP_NUMBER não configurado: links de WhatsApp desativados.")
    return app
