import io
import json
import re

import pytest
from PIL import Image

from app import create_app

PASSWORD = "senha-de-teste-123"


@pytest.fixture()
def app(tmp_path):
    return create_app("testing", {
        "SETTINGS_PATH": str(tmp_path / "site_settings.json"),
        "ADMIN_AUTH_PATH": str(tmp_path / "admin_auth.json"),
        "UPLOAD_FOLDER": str(tmp_path / "uploads"),
    })


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def admin(client):
    r = client.post("/admin/entrar", data={"senha": PASSWORD})
    assert r.status_code == 302
    return client


def html(r):
    return r.get_data(as_text=True)


def form_data(client, page):
    """Lê todos os campos do formulário de uma aba (como o navegador enviaria)."""
    body = html(client.get(f"/admin/editar/{page}"))
    form = body.split("data-edit-form", 1)[1].split("</form>", 1)[0]
    form = re.sub(r"<template.*?</template>", "", form, flags=re.S)
    data = {}
    for tag in re.findall(r"<input\b[^>]*>", form):
        name = re.search(r'name="([^"]+)"', tag)
        if not name or 'type="file"' in tag:
            continue
        if 'type="checkbox"' in tag:
            if "checked" in tag:
                data[name.group(1)] = "1"
            continue
        val = re.search(r'value="([^"]*)"', tag)
        data[name.group(1)] = val.group(1) if val else ""
    for name, val in re.findall(r'<textarea[^>]*name="([^"]+)"[^>]*>(.*?)</textarea>', form, re.S):
        data[name] = val
    for name, opts in re.findall(r'<select[^>]*name="([^"]+)"[^>]*>(.*?)</select>', form, re.S):
        sel = re.search(r'<option value="([^"]*)" selected', opts)
        data[name] = sel.group(1) if sel else ""
    import html as h
    return {k: h.unescape(v) for k, v in data.items()}


def png_bytes(size=(1000, 1200), color=(120, 30, 140)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    buf.seek(0)
    return buf


# ------------------------------------------------------------------ acesso
def test_admin_requires_login(client):
    r = client.get("/admin/")
    assert r.status_code == 302 and "/admin/entrar" in r.headers["Location"]
    assert client.get("/admin/editar/textos").status_code == 302


def test_wrong_password(client):
    r = client.post("/admin/entrar", data={"senha": "errada"})
    assert r.status_code == 401
    assert "Senha incorreta" in html(r)


def test_admin_disabled_without_password(tmp_path):
    app = create_app("testing", {"ADMIN_PASSWORD": "", "SETTINGS_PATH": ""})
    c = app.test_client()
    assert "painel está desativado" in html(c.get("/admin/entrar"))
    assert c.post("/admin/entrar", data={"senha": ""}).status_code == 200
    assert c.get("/admin/").status_code == 302


def test_login_rate_limited():
    app = create_app("testing", {"RATELIMIT_ENABLED": True})
    c = app.test_client()
    codes = [c.post("/admin/entrar", data={"senha": "x"}).status_code for _ in range(6)]
    create_app("testing")
    assert codes[-1] == 429


def test_admin_not_indexed(admin):
    r = admin.get("/admin/")
    assert r.headers["X-Robots-Tag"] == "noindex, nofollow"
    assert r.headers["Cache-Control"] == "no-store"
    assert "Disallow: /admin" in html(admin.get("/robots.txt"))


@pytest.mark.parametrize("page", ["contato", "textos", "servicos", "diferenciais", "avaliacoes",
                                  "conteudos", "seo", "pixels", "aparencia"])
def test_all_admin_pages_render(admin, page):
    r = admin.get(f"/admin/editar/{page}")
    assert r.status_code == 200
    assert "Salvar alterações" in html(r)


def test_other_admin_pages_render(admin):
    for url in ["/admin/", "/admin/fotos", "/admin/backup", "/admin/senha"]:
        assert admin.get(url).status_code == 200, url


def test_unchanged_save_keeps_site_identical(admin, client):
    before = html(client.get("/"))
    for page in ["contato", "textos", "servicos", "diferenciais", "avaliacoes", "conteudos", "seo", "pixels", "aparencia"]:
        r = admin.post(f"/admin/editar/{page}", data=form_data(admin, page))
        assert r.status_code == 302, (page, html(r)[:3000])
    after = html(client.get("/"))
    strip = lambda s: re.sub(r'name="csrf_token"[^>]*>', "", s)
    assert strip(before) == strip(after)


# ------------------------------------------------------------------ edição
def test_edit_texts(admin, client):
    data = form_data(admin, "textos")
    data["f:textos.hero:titulo"] = "Documentos do seu carro sem dor de cabeça."
    data["f:textos.sobre:texto"] = "Primeiro parágrafo.\n\nSegundo parágrafo."
    admin.post("/admin/editar/textos", data=data)
    body = html(client.get("/"))
    assert "Documentos do seu carro sem dor de cabeça." in body
    assert "<p>Primeiro parágrafo.</p>" in body and "<p>Segundo parágrafo.</p>" in body


def test_change_whatsapp_and_phone(admin, client):
    data = form_data(admin, "contato")
    data["f:contato:whatsapp"] = "(21) 99999-8888"
    data["f:contato:telefone"] = "2133334444"
    r = admin.post("/admin/editar/contato", data=data)
    assert r.status_code == 302
    body = html(client.get("/"))
    assert "https://wa.me/5521999998888?text=" in body
    assert "5521972602420" not in body
    assert 'href="tel:+552133334444"' in body and "(21) 3333-4444" in body


def test_invalid_whatsapp_rejected(admin, client):
    data = form_data(admin, "contato")
    data["f:contato:whatsapp"] = "123"
    r = admin.post("/admin/editar/contato", data=data)
    assert r.status_code == 400
    assert "DDD" in html(r)
    assert "5521972602420" in html(client.get("/"))


def test_add_remove_reorder_services(admin, client):
    data = form_data(admin, "servicos")
    for k in [k for k in data if k.startswith("l:servicos:0:")]:
        del data[k]  # remove o primeiro serviço
    data["l:servicos:99:nome"] = "Vistoria veicular"
    data["l:servicos:99:icone"] = "shield-check"
    data["l:servicos:99:descricao"] = "Agendamento de vistoria."
    admin.post("/admin/editar/servicos", data=data)
    body = html(client.get("/servicos"))
    assert "Vistoria veicular" in body and 'id="servico-vistoria-veicular"' in body
    assert "Transferência de propriedade" not in body.split('id="servicos"')[1].split("</section>")[0]
    # o formulário de contato passa a aceitar o novo serviço
    r = client.post("/contato", data={"nome": "Maria Silva", "telefone": "21988887777", "servico": "Vistoria veicular",
                                      "mensagem": "Quero agendar vistoria.", "consent": "y"},
                    headers={"X-Requested-With": "fetch"})
    assert r.get_json()["ok"] is True


def test_hide_review_and_add_review(admin, client):
    data = form_data(admin, "avaliacoes")
    del data["l:avaliacoes:0:visivel"]  # esconde a primeira
    data["l:avaliacoes:500:nome"] = "Cliente Novo"
    data["l:avaliacoes:500:texto"] = "Atendimento nota dez."
    data["l:avaliacoes:500:visivel"] = "1"
    admin.post("/admin/editar/avaliacoes", data=data)
    body = html(client.get("/"))
    assert "Rayssa Bonfim" not in body
    assert "Cliente Novo" in body and "Atendimento nota dez." in body


def test_section_visibility(admin, client):
    data = form_data(admin, "aparencia")
    del data["f:aparencia.secoes:diferenciais"]
    admin.post("/admin/editar/aparencia", data=data)
    assert 'id="diferenciais"' not in html(client.get("/"))


def test_seo_fields(admin, client):
    data = form_data(admin, "seo")
    data["f:seo.paginas.index:titulo"] = "Despachante em Niterói | Jaqueline Sias"
    data["f:seo:google_verificacao"] = '<meta name="google-site-verification" content="abc123XYZ" />'
    data["f:seo:areas_atendidas"] = "Niterói\nSão Gonçalo"
    admin.post("/admin/editar/seo", data=data)
    body = html(client.get("/"))
    assert "<title>Despachante em Niterói | Jaqueline Sias</title>" in body
    assert '<meta name="google-site-verification" content="abc123XYZ">' in body
    ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', body, re.S).group(1))
    biz = next(n for n in ld["@graph"] if n["@type"] == "ProfessionalService")
    assert [a["name"] for a in biz["areaServed"]] == ["Niterói", "São Gonçalo"]


def test_noindex_toggle(admin, client):
    data = form_data(admin, "seo")
    data["f:seo:bloquear_indexacao"] = "1"
    admin.post("/admin/editar/seo", data=data)
    assert 'content="noindex' in html(client.get("/"))


# ------------------------------------------------------------------ pixels
def test_pixels_install_with_consent_and_csp(admin, client):
    data = form_data(admin, "pixels")
    data["f:pixels:ga4"] = "g-abc1234567"
    data["f:pixels:meta"] = "123456789012345"
    r = admin.post("/admin/editar/pixels", data=data)
    assert r.status_code == 302
    r = client.get("/")
    body = html(r)
    cfg = json.loads(re.search(r'<script type="application/json" id="tracking-config">(.*?)</script>', body, re.S).group(1))
    assert cfg["ga4"] == "G-ABC1234567" and cfg["meta"] == "123456789012345" and cfg["consent"] is True
    assert "data-cookie-banner" in body and "tracking.js" in body
    csp = r.headers["Content-Security-Policy"]
    assert "https://www.googletagmanager.com" in csp and "https://connect.facebook.net" in csp
    assert "'unsafe-inline'" not in csp
    assert "não utiliza rastreadores" not in body
    assert "Meta (Facebook/Instagram)" in html(client.get("/privacidade"))


def test_invalid_pixel_rejected(admin):
    data = form_data(admin, "pixels")
    data["f:pixels:ga4"] = "UA-123"
    r = admin.post("/admin/editar/pixels", data=data)
    assert r.status_code == 400 and "G-XXXXXXXXXX" in html(r)


def test_no_tracking_by_default(client):
    body = html(client.get("/"))
    assert "tracking-config" not in body and "cookie-banner" not in body
    assert "não utiliza rastreadores" in body


# ------------------------------------------------------------------ cores
def test_theme_colors(admin, client):
    data = form_data(admin, "aparencia")
    data["f:aparencia.cores:purple"] = "#123456"
    admin.post("/admin/editar/aparencia", data=data)
    body = html(client.get("/"))
    href = re.search(r'href="(/tema\.css\?v=[^"]+)"', body).group(1)
    assert "--purple: #123456;" in html(client.get(href))


# ------------------------------------------------------------------ fotos
def test_upload_hero_photo(admin, client, app):
    r = admin.post("/admin/fotos", data={
        "foto_hero": (png_bytes(), "nova.png"),
        "alt_hero": "Nova foto da Jaqueline", "alt_sobre": "Retrato",
    }, content_type="multipart/form-data")
    assert r.status_code == 302, html(r)
    body = html(client.get("/"))
    src = re.search(r'<img src="(/uploads/hero-[0-9a-f]+\.webp)"', body).group(1)
    img = client.get(src)
    assert img.status_code == 200 and img.mimetype == "image/webp"
    assert Image.open(io.BytesIO(img.data)).size == (700, 840)
    assert 'alt="Nova foto da Jaqueline"' in body


def test_upload_rejects_non_image(admin):
    r = admin.post("/admin/fotos", data={
        "foto_hero": (io.BytesIO(b"<?php echo 1; ?>"), "x.png"),
        "alt_hero": "a", "alt_sobre": "b",
    }, content_type="multipart/form-data")
    assert r.status_code == 400 and "não é uma imagem válida" in html(r)


def test_gallery_add_and_remove(admin, client):
    form = {"alt_hero": "a", "alt_sobre": "b", "g:0:src": "images/team/jaqueline-institucional.webp",
            "g:0:alt": "x", "g:0:remover": "1",
            "galeria_novas": [(png_bytes((800, 800)), "g1.png")]}
    admin.post("/admin/fotos", data=form, content_type="multipart/form-data")
    body = html(client.get("/"))
    assert "jaqueline-institucional" not in body
    assert re.search(r"/uploads/galeria-[0-9a-f]+\.webp", body)


def test_gallery_rejects_arbitrary_paths(admin, client):
    admin.post("/admin/fotos", data={"alt_hero": "a", "alt_sobre": "b", "g:0:src": "../../.env"},
               content_type="multipart/form-data")
    assert ".env" not in html(client.get("/"))


# ------------------------------------------------------------------ reset e backup
def test_reset_page_and_restore_backup(admin, client):
    data = form_data(admin, "textos")
    data["f:textos.hero:titulo"] = "Título temporário"
    admin.post("/admin/editar/textos", data=data)
    admin.post("/admin/editar/textos/restaurar")
    assert "Seu veículo em dia, sem complicação." in html(client.get("/"))
    backups = re.findall(r'name="nome" value="([^"]+)"', html(admin.get("/admin/backup")))
    assert backups
    admin.post("/admin/backup/restaurar", data={"nome": backups[0]})
    assert "Título temporário" in html(client.get("/"))


def test_reset_page_keeps_other_pages(admin, client):
    d1 = form_data(admin, "textos")
    d1["f:textos.hero:titulo"] = "Título novo"
    admin.post("/admin/editar/textos", data=d1)
    d2 = form_data(admin, "servicos")
    d2["f:textos.servicos:titulo"] = "Serviços novos"
    admin.post("/admin/editar/servicos", data=d2)
    admin.post("/admin/editar/textos/restaurar")
    body = html(client.get("/"))
    assert "Título novo" not in body and "Serviços novos" in body


def test_reset_all_requires_confirmation(admin, client):
    data = form_data(admin, "textos")
    data["f:textos.hero:titulo"] = "Outro título"
    admin.post("/admin/editar/textos", data=data)
    admin.post("/admin/restaurar-tudo", data={"confirmacao": "sim"})
    assert "Outro título" in html(client.get("/"))
    admin.post("/admin/restaurar-tudo", data={"confirmacao": "restaurar"})
    assert "Seu veículo em dia, sem complicação." in html(client.get("/"))


def test_export_import(admin, client):
    data = form_data(admin, "textos")
    data["f:textos.hero:titulo"] = "Título exportado"
    admin.post("/admin/editar/textos", data=data)
    exported = admin.get("/admin/backup/exportar")
    assert "attachment" in exported.headers["Content-Disposition"]
    admin.post("/admin/restaurar-tudo", data={"confirmacao": "RESTAURAR"})
    admin.post("/admin/backup/importar", data={"arquivo": (io.BytesIO(exported.data), "b.json")},
               content_type="multipart/form-data")
    assert "Título exportado" in html(client.get("/"))
    r = admin.post("/admin/backup/importar", data={"arquivo": (io.BytesIO(b'{"servicos": "x"}'), "b.json")},
                   content_type="multipart/form-data", follow_redirects=True)
    assert "Arquivo inválido" in html(r)


def test_settings_persist_across_app_instances(tmp_path):
    cfg = {"SETTINGS_PATH": str(tmp_path / "s.json"), "ADMIN_AUTH_PATH": str(tmp_path / "a.json")}
    a1 = create_app("testing", cfg).test_client()
    a1.post("/admin/entrar", data={"senha": PASSWORD})
    data = form_data(a1, "textos")
    data["f:textos.hero:titulo"] = "Persistido"
    a1.post("/admin/editar/textos", data=data)
    a2 = create_app("testing", cfg).test_client()  # outro worker
    assert "Persistido" in html(a2.get("/"))


# ------------------------------------------------------------------ senha
def test_change_password(admin, app):
    r = admin.post("/admin/senha", data={"atual": PASSWORD, "nova": "nova-senha-forte", "confirmacao": "nova-senha-forte"})
    assert r.status_code == 302
    c = app.test_client()
    assert c.post("/admin/entrar", data={"senha": PASSWORD}).status_code == 401
    assert c.post("/admin/entrar", data={"senha": "nova-senha-forte"}).status_code == 302


def test_csrf_enforced_on_admin(tmp_path):
    app = create_app("testing", {"WTF_CSRF_ENABLED": True, "SETTINGS_PATH": str(tmp_path / "s.json")})
    c = app.test_client()
    r = c.post("/admin/entrar", data={"senha": PASSWORD})  # sem token CSRF
    assert r.status_code == 302
    with c.session_transaction() as s:
        assert "admin" not in s
