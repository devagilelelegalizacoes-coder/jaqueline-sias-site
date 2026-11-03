import json
import re
from urllib.parse import unquote

import pytest

from app import create_app

PAGES = ["/", "/servicos", "/sobre", "/contato", "/privacidade", "/conteudo"]

VALID = {
    "nome": "Maria da Silva",
    "telefone": "(21) 98888-7777",
    "servico": "Licenciamento veicular",
    "mensagem": "Gostaria de saber como licenciar meu carro.",
    "consent": "y",
}


@pytest.fixture()
def app():
    return create_app("testing")


@pytest.fixture()
def client(app):
    return app.test_client()


def html(resp):
    return resp.get_data(as_text=True)


# ------------------------------------------------------------------ páginas e SEO
@pytest.mark.parametrize("url", PAGES)
def test_pages_ok_with_seo_basics(client, url):
    r = client.get(url)
    assert r.status_code == 200
    body = html(r)
    assert body.count("<h1") == 1, "cada página deve ter exatamente um H1"
    assert re.search(r"<title>[^<]{10,}</title>", body)
    assert '<meta name="description" content="' in body
    assert '<link rel="canonical" href="https://www.exemplo.com.br' in body
    assert 'property="og:image"' in body
    assert '<html lang="pt-BR">' in body
    for img in re.findall(r"<img\b[^>]*>", body):
        assert re.search(r'\salt="[^"]+"', img), f"imagem sem alt: {img}"


def test_unique_titles_and_descriptions(client):
    titles, descs = set(), set()
    for url in PAGES:
        body = html(client.get(url))
        titles.add(re.search(r"<title>(.*?)</title>", body).group(1))
        descs.add(re.search(r'name="description" content="(.*?)"', body).group(1))
    assert len(titles) == len(PAGES)
    assert len(descs) == len(PAGES)


def test_home_has_all_sections(client):
    body = html(client.get("/"))
    for section in ["inicio", "sobre", "servicos", "diferenciais", "avaliacoes",
                    "como-funciona", "duvidas", "conteudo", "instagram", "contato"]:
        assert f'id="{section}"' in body
    assert "Seu veículo em dia, sem complicação." in body
    assert "Prazer, sou Jaqueline Sias." in body
    assert "Vamos resolver a documentação do seu veículo?" in body


def test_json_ld_is_valid(client):
    body = html(client.get("/"))
    raw = re.search(r'<script type="application/ld\+json">(.*?)</script>', body, re.S).group(1)
    data = json.loads(raw)
    types = {n["@type"] for n in data["@graph"]}
    assert {"WebSite", "ProfessionalService", "FAQPage"} <= types
    biz = next(n for n in data["@graph"] if n["@type"] == "ProfessionalService")
    assert biz["telephone"] == "+5521972602420"
    assert biz["address"]["addressLocality"] == "Niterói"
    assert "aggregateRating" not in biz  # nenhuma nota inventada


def test_sitemap_and_robots(client):
    sm = html(client.get("/sitemap.xml"))
    for url in PAGES:
        assert f"<loc>https://www.exemplo.com.br{url}</loc>" in sm
    rb = client.get("/robots.txt")
    assert rb.mimetype == "text/plain"
    assert "Sitemap: https://www.exemplo.com.br/sitemap.xml" in html(rb)


def test_404_page(client):
    r = client.get("/nao-existe")
    assert r.status_code == 404
    assert "Página não encontrada" in html(r)
    assert 'name="robots" content="noindex' in html(r)


def test_healthcheck(client):
    assert client.get("/healthz").get_json() == {"status": "ok"}


def test_icons_keep_inner_shape_sizes(client):
    body = html(client.get("/"))
    # o ícone "smartphone" é um <rect> com width/height: não pode ser removido
    svg = re.search(r'<svg class="icon icon-smartphone[^"]*".*?</svg>', body, re.S).group(0)
    assert re.search(r'<rect[^>]*width="14"', svg)
    assert 'width="24"' not in svg.split(">")[0]


def test_static_assets_exist(client):
    body = html(client.get("/"))
    assets = set(re.findall(r'(?:src|href)="(/static/[^"?]+)', body))
    assert assets
    for path in assets:
        assert client.get(path).status_code == 200, path


# ------------------------------------------------------------------ WhatsApp / Instagram
def test_whatsapp_links(client):
    body = html(client.get("/"))
    links = re.findall(r'href="(https://wa\.me/[^"]+)"', body)
    assert links
    for link in links:
        assert link.startswith("https://wa.me/5521972602420?text=")
    general = unquote(links[0].split("text=")[1])
    assert general == "Olá, Jaqueline! Acessei seu site e gostaria de informações sobre serviços de despachante."
    assert any("transfer%C3%AAncia%20de%20propriedade" in link for link in links)
    assert 'class="wa-float"' in body
    assert "Fale diretamente comigo" in body


def test_without_whatsapp_number_no_invalid_links(monkeypatch):
    app = create_app("testing")
    app.config["WHATSAPP_NUMBER"] = ""
    body = html(app.test_client().get("/"))
    assert "wa.me" not in body
    assert 'class="wa-float"' not in body
    assert 'href="/contato' in body


def test_instagram_links(client):
    body = html(client.get("/"))
    assert "https://www.instagram.com/jaquelinesiasdespachante/" in body
    assert "@jaquelinesiasdespachante" in body


# ------------------------------------------------------------------ segurança
def test_security_headers(client):
    h = client.get("/").headers
    assert "default-src 'self'" in h["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in h["Content-Security-Policy"]
    assert h["X-Content-Type-Options"] == "nosniff"
    assert h["X-Frame-Options"] == "DENY"
    assert h["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_no_inline_scripts_or_styles(client):
    """CSP estrita: nenhum script/estilo inline (exceto JSON-LD)."""
    for url in PAGES:
        body = html(client.get(url))
        assert " style=" not in body
        assert "<style" not in body
        for tag in re.findall(r"<script\b[^>]*>", body):
            assert "src=" in tag or 'type="application/ld+json"' in tag


def test_env_file_not_served(client):
    assert client.get("/.env").status_code == 404
    assert client.get("/static/../.env").status_code in (400, 404)


def test_csrf_enforced():
    app = create_app("testing")
    app.config["WTF_CSRF_ENABLED"] = True
    r = app.test_client().post("/contato", data=VALID, headers={"X-Requested-With": "fetch"})
    assert r.status_code == 400
    assert r.get_json()["ok"] is False


def test_rate_limit_on_contact():
    app = create_app("testing", {"RATELIMIT_ENABLED": True, "RATELIMIT_CONTACT": "2 per minute"})
    c = app.test_client()
    codes = [c.post("/contato", data=VALID, headers={"X-Requested-With": "fetch"}).status_code for _ in range(3)]
    create_app("testing")  # restaura o limiter desativado para os demais testes
    assert codes[:2] == [200, 200]
    assert codes[2] == 429


# ------------------------------------------------------------------ formulário
def test_contact_ajax_success(client):
    r = client.post("/contato", data=VALID, headers={"X-Requested-With": "fetch"})
    data = r.get_json()
    assert r.status_code == 200 and data["ok"] is True
    assert data["first_name"] == "Maria"
    assert data["wa"].startswith("https://wa.me/5521972602420?text=")


def test_contact_post_redirect_get(client):
    r = client.post("/contato", data=VALID)
    assert r.status_code == 303
    page = html(client.get(r.headers["Location"]))
    assert "Mensagem recebida" in page and ", Maria" in page


@pytest.mark.parametrize("field,value,message", [
    ("nome", "", "Informe seu nome"),
    ("nome", "Jo", "Informe seu nome"),
    ("nome", "<script>", "Use apenas letras"),
    ("telefone", "123", "telefone com DDD"),
    ("mensagem", "curta", "entre 10 e 1500"),
    ("servico", "Serviço inventado", "Not a valid choice"),
])
def test_contact_validation_errors(client, field, value, message):
    data = {**VALID, field: value}
    r = client.post("/contato", data=data, headers={"X-Requested-With": "fetch"})
    assert r.status_code == 400
    assert message in r.get_json()["errors"][field]


def test_contact_requires_consent(client):
    data = {k: v for k, v in VALID.items() if k != "consent"}
    r = client.post("/contato", data=data, headers={"X-Requested-With": "fetch"})
    assert r.status_code == 400
    assert "consent" in r.get_json()["errors"]


def test_contact_html_errors_render(client):
    r = client.post("/contato", data={**VALID, "telefone": "1"})
    assert r.status_code == 400
    assert 'aria-invalid="true"' in html(r)


def test_contact_honeypot_discards(client, app, tmp_path):
    app.config["CONTACT_STORE_ENABLED"] = True
    app.config["CONTACT_STORAGE_PATH"] = str(tmp_path / "c.jsonl")
    r = client.post("/contato", data={**VALID, "website": "http://spam"}, headers={"X-Requested-With": "fetch"})
    assert r.get_json()["ok"] is True
    assert not (tmp_path / "c.jsonl").exists()


def test_contact_is_stored(client, app, tmp_path):
    app.config["CONTACT_STORE_ENABLED"] = True
    app.config["CONTACT_STORAGE_PATH"] = str(tmp_path / "c.jsonl")
    client.post("/contato", data=VALID, headers={"X-Requested-With": "fetch"})
    saved = json.loads((tmp_path / "c.jsonl").read_text(encoding="utf-8").strip())
    assert saved["nome"] == "Maria da Silva"
    assert saved["telefone"] == "(21) 98888-7777"
    assert "ip" not in saved
