"""Rotas da aplicação."""
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

log = logging.getLogger(__name__)
bp = Blueprint("main", __name__)

WA_SERVICE_TEMPLATE = "Olá, Jaqueline! Acessei seu site e gostaria de informações sobre o serviço de {}."


# --------------------------------------------------------------------------- helpers
def _wants_json() -> bool:
    return (
        request.headers.get("X-Requested-With") == "fetch"
        or request.accept_mimetypes.best == "application/json"
    )


def _abs(endpoint: str, **kw) -> str:
    return current_app.config["SITE_URL"] + url_for(endpoint, **kw)


def _services_with_links():
    wa_link = current_app.jinja_env.globals["wa_link"]
    return [
        {**s, "wa": wa_link(WA_SERVICE_TEMPLATE.format(s["name"].lower()))}
        for s in content.SERVICES
    ]


def _business_schema() -> dict:
    cfg = current_app.config
    site = cfg["SITE_URL"]
    data = {
        "@type": "ProfessionalService",
        "@id": f"{site}/#negocio",
        "name": cfg["SITE_NAME"],
        "description": "Assessoria em serviços e documentação veicular com atendimento personalizado, praticidade e confiança.",
        "url": f"{site}/",
        "image": site + url_for("static", filename="images/team/jaqueline-hero.webp"),
        "logo": site + url_for("static", filename="images/branding/logo-horizontal.png"),
        "founder": {"@type": "Person", "name": "Jaqueline Sias", "jobTitle": "Despachante"},
        "sameAs": [cfg["INSTAGRAM_URL"]] if cfg["INSTAGRAM_URL"] else [],
        "knowsAbout": [s["name"] for s in content.SERVICES],
        "hasOfferCatalog": {
            "@type": "OfferCatalog",
            "name": "Serviços de despachante veicular",
            "itemListElement": [
                {"@type": "Offer", "itemOffered": {"@type": "Service", "name": s["name"], "description": s["desc"]}}
                for s in content.SERVICES
            ],
        },
    }
    if cfg["WHATSAPP_NUMBER"]:
        data["telephone"] = "+" + cfg["WHATSAPP_NUMBER"]
    if cfg["CONTACT_EMAIL"]:
        data["email"] = cfg["CONTACT_EMAIL"]
    if cfg["BUSINESS_CITY"]:
        address = {"@type": "PostalAddress", "addressLocality": cfg["BUSINESS_CITY"], "addressCountry": "BR"}
        if cfg["BUSINESS_STATE"]:
            address["addressRegion"] = cfg["BUSINESS_STATE"]
        if cfg["BUSINESS_ADDRESS"]:
            address["streetAddress"] = cfg["BUSINESS_ADDRESS"]
        if cfg["BUSINESS_POSTAL_CODE"]:
            address["postalCode"] = cfg["BUSINESS_POSTAL_CODE"]
        data["address"] = address
        data["areaServed"] = {"@type": "City", "name": cfg["BUSINESS_CITY"]}
    return data


def _json_ld(*nodes) -> Markup:
    graph = {"@context": "https://schema.org", "@graph": [n for n in nodes if n]}
    raw = json.dumps(graph, ensure_ascii=False, separators=(",", ":"))
    return Markup(raw.replace("</", "<\\/"))


def _faq_schema() -> dict:
    return {
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
            for f in content.FAQS
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


def _page(template: str, *, title: str, description: str, endpoint: str, schema=(), **ctx):
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
    loc = current_app.jinja_env.globals["location_label"]()
    suffix = f" em {loc}" if loc else ""
    website = {"@type": "WebSite", "@id": current_app.config["SITE_URL"] + "/#site",
               "url": _abs("main.index"), "name": current_app.config["SITE_NAME"], "inLanguage": "pt-BR"}
    return _page(
        "index.html",
        title=f"Jaqueline Sias Despachante · Documentação veicular{suffix}",
        description=f"Despachante veicular{suffix}: transferência, licenciamento, primeiro emplacamento e regularização de documentos com atendimento personalizado. Fale pelo WhatsApp.",
        endpoint="main.index",
        schema=(website, _business_schema(), _faq_schema()),
    )


@bp.get("/servicos")
def servicos():
    loc = current_app.jinja_env.globals["location_label"]()
    suffix = f" em {loc}" if loc else ""
    return _page(
        "servicos.html",
        title=f"Serviços de despachante veicular{suffix} · Jaqueline Sias",
        description="Transferência de propriedade, primeiro emplacamento, licenciamento, regularização documental, consulta de débitos, segunda via e alteração de características.",
        endpoint="main.servicos",
        schema=(_business_schema(), _faq_schema(), _breadcrumb("Serviços", "main.servicos")),
    )


@bp.get("/sobre")
def sobre():
    return _page(
        "sobre.html",
        title="Sobre Jaqueline Sias · Despachante",
        description="Conheça Jaqueline Sias: atendimento próximo, comunicação transparente e documentação veicular conduzida com responsabilidade.",
        endpoint="main.sobre",
        schema=(_business_schema(), _breadcrumb("Sobre", "main.sobre")),
    )


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
        title="Contato · Jaqueline Sias Despachante",
        description="Vamos resolver a documentação do seu veículo? Fale com Jaqueline Sias pelo WhatsApp ou envie uma mensagem pelo formulário.",
        endpoint="main.contato",
        schema=(_business_schema(), _breadcrumb("Contato", "main.contato")),
        form=form,
    ), (400 if request.method == "POST" else 200)


@bp.get("/privacidade")
def privacidade():
    return _page(
        "privacidade.html",
        title="Política de Privacidade · Jaqueline Sias Despachante",
        description="Como os dados enviados pelo site da Jaqueline Sias Despachante são coletados, usados e protegidos, conforme a LGPD.",
        endpoint="main.privacidade",
        schema=(_breadcrumb("Política de Privacidade", "main.privacidade"),),
        updated=date(2026, 11, 2),
    )


@bp.get("/conteudo")
def conteudo():
    return _page(
        "conteudo.html",
        title="Informação que facilita sua vida · Jaqueline Sias Despachante",
        description="Orientações sobre documentação veicular, legislação de trânsito, cuidados com o veículo e processos administrativos.",
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
    body = f"User-agent: *\nAllow: /\nDisallow: /healthz\n\nSitemap: {_abs('main.sitemap')}\n"
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
        "background_color": "#3E0A4F",
        "theme_color": "#3E0A4F",
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
        msg = "Muitas tentativas em pouco tempo. Aguarde alguns minutos ou fale pelo WhatsApp."
        if _wants_json():
            return jsonify(ok=False, message=msg), 429
        flash(msg, "error")
        return redirect(url_for("main.contato") + "#formulario")

    @app.errorhandler(CSRFError)
    def csrf_error(_e):
        msg = "Sua sessão expirou. Atualize a página e envie novamente."
        if _wants_json():
            return jsonify(ok=False, message=msg), 400
        flash(msg, "error")
        return redirect(url_for("main.contato") + "#formulario")
