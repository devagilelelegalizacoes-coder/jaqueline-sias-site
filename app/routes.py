"""Rotas da aplicação."""
import hashlib
import json
import logging
from datetime import date

from flask import (Blueprint, Response, abort, current_app, flash, jsonify, redirect,
                   render_template, request, send_from_directory, session, url_for)
from flask_wtf.csrf import CSRFError
from markupsafe import Markup

from . import content, limiter
from .contact import deliver
from .forms import ContactForm
from .settings_store import DEFAULT_COLORS, get_settings, slugify

log = logging.getLogger(__name__)
bp = Blueprint("main", __name__)


# --------------------------------------------------------------------------- helpers
def _wants_json() -> bool:
    return (
        request.headers.get("X-Requested-With") == "fetch"
        or request.accept_mimetypes.best == "application/json"
    )


def _abs(endpoint: str, **kw) -> str:
    return current_app.config["SITE_URL"] + url_for(endpoint, **kw)


def _services_with_links():
    site = get_settings()
    wa_link = current_app.jinja_env.globals["wa_link"]
    template = site["textos"]["servicos"]["mensagem_whatsapp"] or "{servico}"
    out = []
    for s in site["servicos"]:
        try:
            msg = template.format(servico=s["nome"].lower())
        except (KeyError, IndexError, ValueError):
            msg = template
        out.append({**s, "slug": slugify(s["nome"]), "wa": wa_link(msg)})
    return out


def _business_schema() -> dict:
    cfg = current_app.config
    site_cfg = get_settings()
    c, seo = site_cfg["contato"], site_cfg["seo"]
    media = current_app.jinja_env.globals["media"]
    site = cfg["SITE_URL"]
    services = site_cfg["servicos"]
    data = {
        "@type": "ProfessionalService",
        "@id": f"{site}/#negocio",
        "name": cfg["SITE_NAME"],
        "description": seo["descricao_negocio"],
        "url": f"{site}/",
        "image": media(site_cfg["fotos"]["hero"], _external=True),
        "logo": media(site_cfg["fotos"]["logo_png"], _external=True),
        "sameAs": [c["instagram_url"]] if c["instagram_url"] else [],
        "knowsAbout": [s["nome"] for s in services],
        "hasOfferCatalog": {
            "@type": "OfferCatalog",
            "name": "Serviços de despachante veicular",
            "itemListElement": [
                {"@type": "Offer", "itemOffered": {"@type": "Service", "name": s["nome"], "description": s["descricao"]}}
                for s in services
            ],
        },
    }
    if seo["responsavel"]:
        data["founder"] = {"@type": "Person", "name": seo["responsavel"], "jobTitle": "Despachante"}
    if c["whatsapp"]:
        data["telephone"] = "+" + c["whatsapp"]
    if c["email"]:
        data["email"] = c["email"]
    if c["horario"]:
        data["openingHours"] = c["horario"]
    if c["cidade"]:
        address = {"@type": "PostalAddress", "addressLocality": c["cidade"], "addressCountry": "BR"}
        if c["estado"]:
            address["addressRegion"] = c["estado"]
        if c["endereco"]:
            address["streetAddress"] = c["endereco"]
        if c["cep"]:
            address["postalCode"] = c["cep"]
        data["address"] = address
    areas = [a.strip() for a in seo["areas_atendidas"].splitlines() if a.strip()] or ([c["cidade"]] if c["cidade"] else [])
    if areas:
        places = [{"@type": "City", "name": a} for a in areas]
        data["areaServed"] = places[0] if len(places) == 1 else places
    return data


def _json_ld(*nodes) -> Markup:
    graph = {"@context": "https://schema.org", "@graph": [n for n in nodes if n]}
    raw = json.dumps(graph, ensure_ascii=False, separators=(",", ":"))
    return Markup(raw.replace("</", "<\\/"))


def _faq_schema() -> dict | None:
    site = get_settings()
    if not site["faq"] or not site["aparencia"]["secoes"]["faq"]:
        return None
    return {
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": f["pergunta"], "acceptedAnswer": {"@type": "Answer", "text": f["resposta"]}}
            for f in site["faq"]
        ],
    }


def _breadcrumb(name: str, endpoint: str) -> dict:
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Início", "item": _abs("main.index")},
            {"@type": "ListItem", "position": 2, "name": name, "item": _abs(endpoint)},
        ],
    }


def _page(template: str, *, seo_key: str | None = None, title: str = "", description: str = "",
          endpoint: str, schema=(), **ctx):
    if seo_key:
        meta = get_settings()["seo"]["paginas"][seo_key]
        title, description = meta["titulo"], meta["descricao"]
    contact_ok = session.pop("contact_ok", None)
    return render_template(
        template,
        page_title=title,
        meta_description=description,
        canonical=_abs(endpoint, **ctx.pop("endpoint_kw", {})),
        json_ld=_json_ld(*schema),
        services=_services_with_links(),
        content=content,
        form=ctx.pop("form", None) or ContactForm(),
        contact_ok=contact_ok,
        **ctx,
    )


# --------------------------------------------------------------------------- páginas
@bp.get("/")
def index():
    website = {"@type": "WebSite", "@id": current_app.config["SITE_URL"] + "/#site",
               "url": _abs("main.index"), "name": current_app.config["SITE_NAME"], "inLanguage": "pt-BR"}
    return _page("index.html", seo_key="index", endpoint="main.index",
                 schema=(website, _business_schema(), _faq_schema()))


@bp.get("/servicos")
def servicos():
    return _page("servicos.html", seo_key="servicos", endpoint="main.servicos",
                 schema=(_business_schema(), _faq_schema(), _breadcrumb("Serviços", "main.servicos")))


@bp.get("/sobre")
def sobre():
    return _page("sobre.html", seo_key="sobre", endpoint="main.sobre",
                 schema=(_business_schema(), _breadcrumb("Sobre", "main.sobre")))


@bp.route("/contato", methods=["GET", "POST"])
@limiter.limit(lambda: current_app.config["RATELIMIT_CONTACT"], methods=["POST"])
def contato():
    form = ContactForm()
    if request.method == "POST":
        if form.validate_on_submit():
            first_name = form.nome.data.split(" ")[0]
            servico = form.servico.data or ""
            wa_msg = (
                f"Olá, Jaqueline! Sou {form.nome.data} e acabei de enviar uma mensagem pelo site"
                + (f" sobre {servico.lower()}." if servico and servico != "Outro assunto" else ".")
            )
            wa = current_app.jinja_env.globals["wa_link"](wa_msg)
            if form.is_spam:
                log.info("Envio descartado pelo honeypot")
                ok = True
            else:
                ok = deliver(form.nome.data, form.formatted_phone(), servico, form.mensagem.data)
            if not ok:
                msg = "Não foi possível enviar agora. Tente novamente ou fale pelo WhatsApp."
                if _wants_json():
                    return jsonify(ok=False, message=msg, wa=wa), 503
                flash(msg, "error")
                return redirect(url_for("main.contato") + "#formulario")
            if _wants_json():
                return jsonify(ok=True, first_name=first_name, wa=wa)
            session["contact_ok"] = {"first_name": first_name, "wa": wa}
            return redirect(url_for("main.contato") + "#formulario", code=303)

        if _wants_json():
            errors = {k: v[0] for k, v in form.errors.items() if k != "website"}
            return jsonify(ok=False, errors=errors), 400

    return _page(
        "contato.html",
        seo_key="contato",
        endpoint="main.contato",
        schema=(_business_schema(), _breadcrumb("Contato", "main.contato")),
        form=form,
    ), (400 if request.method == "POST" else 200)


@bp.get("/privacidade")
def privacidade():
    return _page(
        "privacidade.html",
        seo_key="privacidade",
        endpoint="main.privacidade",
        schema=(_breadcrumb("Política de Privacidade", "main.privacidade"),),
        updated=date(2026, 11, 2),
    )


@bp.get("/conteudo")
def conteudo():
    return _page(
        "conteudo.html",
        seo_key="conteudo",
        endpoint="main.conteudo",
        schema=(_breadcrumb("Conteúdo", "main.conteudo"),),
    )


@bp.get("/conteudo/<slug>")
def artigo(slug: str):
    article = next((a for a in content.ARTICLES if a["slug"] == slug), None)
    if not article:
        abort(404)
    return _page(
        f"artigos/{slug}.html",
        title=f"{article['title']} · Jaqueline Sias Despachante",
        description=article["description"],
        endpoint="main.artigo",
        endpoint_kw={"slug": slug},
        article=article,
    )


# --------------------------------------------------------------------------- SEO / infra
@bp.get("/robots.txt")
def robots():
    body = (f"User-agent: *\nAllow: /\nDisallow: /healthz\nDisallow: /admin\n\n"
            f"Sitemap: {_abs('main.sitemap')}\n")
    return Response(body, mimetype="text/plain")


@bp.get("/sitemap.xml")
def sitemap():
    today = date.today().isoformat()
    pages = [("main.index", "1.0"), ("main.servicos", "0.9"), ("main.sobre", "0.8"),
             ("main.contato", "0.8"), ("main.conteudo", "0.5"), ("main.privacidade", "0.3")]
    urls = [(_abs(ep), today, prio) for ep, prio in pages]
    urls += [(_abs("main.artigo", slug=a["slug"]), a.get("date", today), "0.6") for a in content.ARTICLES]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, mod, prio in urls:
        xml.append(f"  <url><loc>{loc}</loc><lastmod>{mod}</lastmod><priority>{prio}</priority></url>")
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype="application/xml")


@bp.get("/site.webmanifest")
def manifest():
    data = {
        "name": current_app.config["SITE_NAME"],
        "short_name": "Jaqueline Sias",
        "start_url": "/",
        "display": "standalone",
        "background_color": get_settings()["aparencia"]["cores"]["purple_deep"],
        "theme_color": get_settings()["aparencia"]["cores"]["purple_deep"],
        "lang": "pt-BR",
        "icons": [
            {"src": url_for("static", filename="images/favicon/icon-192.png"), "sizes": "192x192", "type": "image/png"},
            {"src": url_for("static", filename="images/favicon/icon-512.png"), "sizes": "512x512", "type": "image/png"},
        ],
    }
    return Response(json.dumps(data, ensure_ascii=False), mimetype="application/manifest+json")


@bp.get("/favicon.ico")
def favicon():
    return send_from_directory(current_app.static_folder, "favicon.ico", mimetype="image/vnd.microsoft.icon")


@bp.get("/uploads/<path:filename>")
def uploaded(filename: str):
    """Fotos enviadas pelo painel (nomes aleatórios: cache longo)."""
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename, max_age=60 * 60 * 24 * 365)


COLOR_VARS = {
    "purple": "--purple", "purple_deep": "--purple-deep", "purple_night": "--purple-night",
    "gold": "--gold", "gold_light": "--gold-light", "gold_dark": "--gold-dark",
}


def theme_css_text(colors: dict) -> str:
    c = colors
    lines = [f"  {var}: {c[key]};" for key, var in COLOR_VARS.items()]
    lines += [
        f"  --gradient: linear-gradient(135deg, {c['purple']} 0%, {c['purple_deep']} 100%);",
        f"  --gradient-alt: linear-gradient(160deg, {c['purple_deep']} 0%, {c['purple']} 100%);",
        f"  --gold-gradient: linear-gradient(90deg, {c['gold_dark']}, {c['gold_light']}, {c['gold']});",
    ]
    return ":root {\n" + "\n".join(lines) + "\n}\n"


@bp.app_template_global()
def theme_version() -> str | None:
    """Hash das cores personalizadas, ou None quando as cores são as originais."""
    colors = get_settings()["aparencia"]["cores"]
    if colors == DEFAULT_COLORS:
        return None
    return hashlib.md5(json.dumps(colors, sort_keys=True).encode(), usedforsecurity=False).hexdigest()[:10]


@bp.get("/tema.css")
def theme_css():
    resp = Response(theme_css_text(get_settings()["aparencia"]["cores"]), mimetype="text/css")
    resp.headers["Cache-Control"] = "public, max-age=31536000" if request.args.get("v") else "no-cache"
    return resp


@bp.get("/healthz")
@limiter.exempt
def healthz():
    return jsonify(status="ok")


# --------------------------------------------------------------------------- erros
def register_error_handlers(app):
    def _render_error(code: int, title: str, template: str):
        if _wants_json():
            return jsonify(ok=False, message=title), code
        return render_template(template, page_title=f"{title} · {app.config['SITE_NAME']}",
                               meta_description=title, canonical=None, noindex=True), code

    @app.errorhandler(404)
    def not_found(_e):
        return _render_error(404, "Página não encontrada", "errors/404.html")

    @app.errorhandler(500)
    def server_error(e):
        log.error("Erro interno: %s", e)
        return _render_error(500, "Erro interno", "errors/500.html")

    @app.errorhandler(429)
    def too_many(_e):
        if request.path.startswith("/admin"):
            flash("Muitas tentativas de login. Aguarde alguns minutos.", "error")
            return render_template("admin/login.html", enabled=True, next=""), 429
        msg = "Muitas tentativas em pouco tempo. Aguarde alguns minutos ou fale pelo WhatsApp."
        if _wants_json():
            return jsonify(ok=False, message=msg), 429
        flash(msg, "error")
        return redirect(url_for("main.contato") + "#formulario")

    @app.errorhandler(CSRFError)
    def csrf_error(_e):
        msg = "Sua sessão expirou. Atualize a página e envie novamente."
        if request.path.startswith("/admin"):
            flash(msg + " Nada foi salvo.", "error")
            target = request.path if request.path.startswith("/admin/editar/") else url_for("admin.dashboard")
            return redirect(target.removesuffix("/restaurar"))
        if _wants_json():
            return jsonify(ok=False, message=msg), 400
        flash(msg, "error")
        return redirect(url_for("main.contato") + "#formulario")
