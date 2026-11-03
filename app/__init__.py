"""Fábrica da aplicação Flask — Jaqueline Sias Despachante."""
import hashlib
import logging
import re
import sys
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv
from flask import Flask, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from markupsafe import Markup
from werkzeug.middleware.proxy_fix import ProxyFix

load_dotenv()

from .config import get_config  # noqa: E402

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
        number = app.config["WHATSAPP_NUMBER"]
        if not number or len(number) < 12:
            return None
        text = message or app.config["WHATSAPP_DEFAULT_MESSAGE"]
        return f"https://wa.me/{number}?text={quote(text, safe='')}"

    def phone_display() -> str | None:
        n = app.config["WHATSAPP_NUMBER"]
        if n.startswith("55") and len(n) in (12, 13):
            local = n[2:]
            if len(local) == 11:
                return f"({local[:2]}) {local[2:7]}-{local[7:]}"
            return f"({local[:2]}) {local[2:6]}-{local[6:]}"
        return None

    def location_label() -> str:
        c, s = app.config["BUSINESS_CITY"], app.config["BUSINESS_STATE"]
        return ", ".join(p for p in (c, s) if p)

    app.jinja_env.globals.update(
        asset=asset, icon=icon, wa_link=wa_link, phone_display=phone_display,
        location_label=location_label,
    )
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True

    @app.context_processor
    def inject_site():
        from datetime import date
        return {"cfg": app.config, "current_year": date.today().year}


def _register_security_headers(app: Flask) -> None:
    frame_src = "https://www.google.com" if app.config["MAPS_EMBED_URL"] else "'none'"
    csp = "; ".join([
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data:",
        "font-src 'self'",
        "connect-src 'self'",
        f"frame-src {frame_src}",
        "form-action 'self'",
        "base-uri 'self'",
        "frame-ancestors 'none'",
        "object-src 'none'",
    ])

    @app.after_request
    def set_headers(resp):
        h = resp.headers
        h.setdefault("Content-Security-Policy", csp)
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("X-Frame-Options", "DENY")
        h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        h.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=(), interest-cohort=()")
        h.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        if app.config["SESSION_COOKIE_SECURE"]:
            h.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if resp.mimetype == "text/html":
            h["Cache-Control"] = "no-cache"
        return resp


def create_app(config_name: str | None = None, overrides: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(get_config(config_name))
    if overrides:
        app.config.update(overrides)
    _configure_logging(app)

    if app.config["TRUST_PROXY"]:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    csrf.init_app(app)
    app.config["RATELIMIT_DEFAULTS"] = [app.config["RATELIMIT_DEFAULT"]]
    limiter.init_app(app)

    _register_template_helpers(app)
    _register_security_headers(app)

    from .routes import bp, register_error_handlers
    app.register_blueprint(bp)
    register_error_handlers(app)

    if not app.config["WHATSAPP_NUMBER"]:
        app.logger.warning("WHATSAPP_NUMBER não configurado: links de WhatsApp desativados.")
    return app
