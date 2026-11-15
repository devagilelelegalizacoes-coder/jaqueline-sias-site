"""Painel administrativo (/admin): edição de textos, listas, fotos, SEO, pixels e aparência."""
import copy
import hashlib
import hmac
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path

from flask import (Blueprint, Response, abort, current_app, flash, g, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from . import limiter
from .admin_schema import ICONS, PIXEL_PATTERNS, resolve_pages
from .media import ImageError, save_cropped, save_gallery, save_logo
from .settings_store import (SECTIONS, defaults, get_settings, invalidate, store,
                             tracking_enabled)

log = logging.getLogger(__name__)
bp = Blueprint("admin", __name__, url_prefix="/admin")
PAGES = resolve_pages(SECTIONS)
MAX_GALLERY = 12
MIN_PASSWORD = 10


# =========================================================================== autenticação
def _auth_path() -> Path | None:
    p = current_app.config.get("ADMIN_AUTH_PATH")
    return Path(p) if p else None


def _stored_hash() -> str | None:
    path = _auth_path()
    if path is None:
        return current_app.extensions.get("admin_auth_hash")
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("hash")
    except (OSError, ValueError):
        return None


def _current_hash() -> str | None:
    """Hash da senha: a definida no painel tem prioridade sobre a do .env."""
    stored = _stored_hash()
    if stored:
        return stored
    cfg = current_app.config
    if cfg.get("ADMIN_PASSWORD_HASH"):
        return cfg["ADMIN_PASSWORD_HASH"]
    if cfg.get("ADMIN_PASSWORD"):
        return "plain:" + cfg["ADMIN_PASSWORD"]
    return None


def _check(password: str, hashed: str) -> bool:
    if hashed.startswith("plain:"):
        return hmac.compare_digest(password.encode(), hashed[6:].encode())
    try:
        return check_password_hash(hashed, password)
    except ValueError:
        return False


def _fingerprint(hashed: str) -> str:
    key = current_app.config["SECRET_KEY"].encode()
    return hmac.new(key, hashed.encode(), hashlib.sha256).hexdigest()[:24]


def is_logged_in() -> bool:
    hashed = _current_hash()
    token = session.get("admin")
    return bool(hashed and token and hmac.compare_digest(token, _fingerprint(hashed)))


def _save_password(new_password: str) -> None:
    hashed = generate_password_hash(new_password)
    path = _auth_path()
    if path is None:
        current_app.extensions["admin_auth_hash"] = hashed
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"hash": hashed, "alterada_em": datetime.now().isoformat(timespec="seconds")}),
                        encoding="utf-8")
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    session["admin"] = _fingerprint(hashed)


@bp.before_request
def _require_login():
    g.admin_area = True
    if request.endpoint in ("admin.login",):
        return None
    if not is_logged_in():
        nxt = request.full_path if request.method == "GET" else url_for("admin.dashboard")
        return redirect(url_for("admin.login", next=nxt.rstrip("?")))
    return None


@bp.after_request
def _no_cache(resp):
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    return resp


@bp.context_processor
def _admin_ctx():
    return {"admin_pages": PAGES, "icons": ICONS}


@bp.route("/entrar", methods=["GET", "POST"])
@limiter.limit("5 per minute;30 per hour", methods=["POST"])
def login():
    enabled = _current_hash() is not None
    nxt = request.values.get("next", "")
    if not nxt.startswith("/admin") or nxt.startswith("//"):
        nxt = url_for("admin.dashboard")
    if is_logged_in():
        return redirect(nxt)
    if request.method == "POST" and enabled:
        hashed = _current_hash()
        if _check(request.form.get("senha", ""), hashed):
            session.clear()
            session.permanent = True
            session["admin"] = _fingerprint(hashed)
            log.info("Login no painel administrativo")
            return redirect(nxt)
        log.warning("Tentativa de login no painel com senha incorreta")
        flash("Senha incorreta.", "error")
        return render_template("admin/login.html", enabled=enabled, next=nxt), 401
    return render_template("admin/login.html", enabled=enabled, next=nxt)


@bp.post("/sair")
def logout():
    session.pop("admin", None)
    flash("Você saiu do painel.", "ok")
    return redirect(url_for("admin.login"))


@bp.route("/senha", methods=["GET", "POST"])
def password():
    if request.method == "POST":
        atual, nova, conf = (request.form.get(k, "") for k in ("atual", "nova", "confirmacao"))
        if not _check(atual, _current_hash()):
            flash("A senha atual está incorreta.", "error")
        elif len(nova) < MIN_PASSWORD:
            flash(f"A nova senha precisa ter pelo menos {MIN_PASSWORD} caracteres.", "error")
        elif nova != conf:
            flash("A confirmação não confere com a nova senha.", "error")
        else:
            _save_password(nova)
            flash("Senha alterada.", "ok")
            return redirect(url_for("admin.dashboard"))
        return render_template("admin/senha.html"), 400
    return render_template("admin/senha.html")


# =========================================================================== validação
EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}")
VERIFY_RE = re.compile(r"[A-Za-z0-9_\-=.:+/]{1,200}")


def _phone_digits(raw: str) -> str | None:
    d = re.sub(r"\D", "", raw)
    if len(d) in (10, 11):
        return "55" + d
    if d.startswith("55") and len(d) in (12, 13):
        return d
    return None


def format_phone(digits: str) -> str:
    d = re.sub(r"\D", "", digits or "")
    if d.startswith("55") and len(d) in (12, 13):
        d = d[2:]
    if len(d) == 11:
        return f"({d[:2]}) {d[2:7]}-{d[7:]}"
    if len(d) == 10:
        return f"({d[:2]}) {d[2:6]}-{d[6:]}"
    return digits or ""


def parse_value(spec: dict, raw, where: str, errors: list):
    t, key = spec["type"], spec["key"]

    def err(msg):
        errors.append(f"{where} › {spec['label']}: {msg}")
        return raw

    if t == "bool":
        return raw is not None
    raw = (raw or "").replace("\r\n", "\n").strip()
    if spec.get("maxlength") and len(raw) > spec["maxlength"]:
        return err(f"máximo de {spec['maxlength']} caracteres.")
    if spec.get("required") and not raw:
        return err("campo obrigatório.")
    if not raw and t not in ("int", "color", "select", "icon"):
        return ""

    if t == "whatsapp":
        return _phone_digits(raw) or err("informe DDD + número, ex.: (21) 97260-2420.")
    if t == "phone":
        d = _phone_digits(raw)
        return format_phone(d) if d else err("informe DDD + número.")
    if t == "email":
        return raw if EMAIL_RE.fullmatch(raw) else err("e-mail inválido.")
    if t == "url":
        ok = re.fullmatch(r"https?://\S+", raw) and len(raw) <= 500
        return raw if ok else err("o link deve começar com https://")
    if t == "maps":
        m = re.search(r'src="([^"]+)"', raw)
        raw = m.group(1) if m else raw
        ok = raw.startswith("https://www.google.com/maps/embed") and " " not in raw and len(raw) <= 2000
        return raw if ok else err("use o link de incorporação (https://www.google.com/maps/embed?...).")
    if t == "uf":
        return raw.upper() if re.fullmatch(r"[A-Za-z]{2}", raw) else err("use a sigla com 2 letras.")
    if t == "color":
        return raw.upper() if re.fullmatch(r"#[0-9A-Fa-f]{6}", raw) else err("cor inválida.")
    if t == "int":
        try:
            n = int(raw)
        except ValueError:
            return err("informe um número.")
        if not spec.get("min", n) <= n <= spec.get("max", n):
            return err(f"use um número entre {spec['min']} e {spec['max']}.")
        return n
    if t == "select":
        return raw if raw in spec["options"] else err("opção inválida.")
    if t == "icon":
        return raw if raw in ICONS else err("ícone inválido.")
    if t == "pixel":
        pattern, example = PIXEL_PATTERNS[key]
        value = raw if key in ("google_ads_rotulo",) else (raw.lower() if key == "clarity" else raw.upper())
        if key == "google_ads" and value.isdigit():
            value = "AW-" + value
        return value if re.fullmatch(pattern, value) else err(f"formato esperado: {example}")
    if t == "verification":
        m = re.search(r'content="([^"]+)"', raw)
        value = m.group(1) if m else raw
        return value if VERIFY_RE.fullmatch(value) else err("cole apenas o código (ou a tag <meta> inteira).")
    return raw  # text, textarea, code


def _get_in(data, path):
    for key in path:
        data = data[key]
    return data


def _parse_list(block: dict, errors: list) -> list:
    rx = re.compile(rf"^l:{re.escape(block['id'])}:(\d+):(\w+)$")
    rows: dict[int, dict] = {}
    for name in request.form:
        m = rx.match(name)
        if m:
            rows.setdefault(int(m.group(1)), {})
    items = []
    for n, idx in enumerate(sorted(rows), start=1):
        prefix = f"l:{block['id']}:{idx}:"
        texts = [request.form.get(prefix + f["key"], "").strip() for f in block["fields"] if f["type"] != "bool"]
        if not any(texts):
            continue  # linha em branco
        where = f"{block['item_label']} {n}"
        item = {f["key"]: parse_value(f, request.form.get(prefix + f["key"]), where, errors) for f in block["fields"]}
        items.append(item)
    if len(items) > block.get("max_items", 100):
        errors.append(f"{block['title']}: máximo de {block['max_items']} itens.")
    return items


# =========================================================================== páginas
@bp.get("/")
def dashboard():
    site = get_settings()
    return render_template("admin/dashboard.html", site=site, checks=seo_checks(site),
                           tracking=tracking_enabled(site))


@bp.route("/editar/<page>", methods=["GET", "POST"])
def edit(page):
    spec = PAGES.get(page) or abort(404)
    data = copy.deepcopy(get_settings())
    status = 200
    if request.method == "POST":
        errors: list[str] = []
        merged: dict[tuple, dict] = {}
        lists: list[tuple[tuple, list]] = []
        for block in spec["blocks"]:
            if block["kind"] == "fields":
                vals = {f["key"]: parse_value(f, request.form.get(f"f:{block['id']}:{f['key']}"), block["title"], errors)
                        for f in block["fields"]}
                merged.setdefault(block["path"], {}).update(vals)
                _get_in(data, block["path"]).update(vals)
            else:
                items = _parse_list(block, errors)
                lists.append((block["path"], items))
                data[block["path"][0]] = items
        if not errors:
            store().save(list(merged.items()) + lists)
            invalidate()
            log.info("Painel: aba '%s' atualizada", page)
            flash("Alterações salvas. Já estão no site.", "ok")
            return redirect(url_for("admin.edit", page=page))
        for e in errors:
            flash(e, "error")
        status = 400
    return render_template("admin/form.html", page_key=page, page=spec, data=data,
                           format_phone=format_phone), status


def _page_paths(spec) -> list[tuple]:
    paths = []
    for block in spec["blocks"]:
        if block["kind"] == "fields":
            paths += [block["path"] + (f["key"],) for f in block["fields"]]
        else:
            paths.append(block["path"])
    return paths


@bp.post("/editar/<page>/restaurar")
def reset_page(page):
    spec = PAGES.get(page) or abort(404)
    if store().reset(_page_paths(spec)):
        flash(f"\"{spec['title']}\" voltou ao conteúdo original. Um backup foi salvo.", "ok")
    else:
        flash("Esta aba já está com o conteúdo original.", "ok")
    invalidate()
    return redirect(url_for("admin.edit", page=page))


# =========================================================================== fotos
PHOTO_SLOTS = {
    "hero": ("Foto do topo da página inicial", "Recortada em 700 × 840 px (retrato)."),
    "sobre": ("Foto da seção Sobre", "Recortada em 900 × 1050 px (retrato)."),
}


@bp.route("/fotos", methods=["GET", "POST"])
def photos():
    site = get_settings()
    fotos = copy.deepcopy(site["fotos"])
    if request.method == "POST":
        errors: list[str] = []
        base = defaults()["fotos"]

        def handle(slot, fn):
            f = request.files.get(f"foto_{slot}")
            if f and f.filename:
                try:
                    return fn(f)
                except ImageError as exc:
                    errors.append(f"{slot}: {exc}")
            return None

        for slot in PHOTO_SLOTS:
            if request.form.get(f"padrao_{slot}"):
                fotos[slot], fotos[f"{slot}_pequena"] = base[slot], base[f"{slot}_pequena"]
            elif out := handle(slot, lambda f, s=slot: save_cropped(f, s)):
                fotos[slot], fotos[f"{slot}_pequena"] = out["src"], out["small"]
            alt = request.form.get(f"alt_{slot}", "").strip()[:200]
            if not alt:
                errors.append(f"{PHOTO_SLOTS[slot][0]}: escreva a descrição da foto (importante para SEO e acessibilidade).")
            fotos[f"{slot}_alt"] = alt

        if request.form.get("padrao_logo"):
            for k in ("logo", "logo_png", "logo_largura", "logo_altura"):
                fotos[k] = base[k]
        elif out := handle("logo", save_logo):
            fotos.update(logo=out["src"], logo_png=out["png"], logo_largura=out["w"], logo_altura=out["h"])

        if request.form.get("padrao_og"):
            fotos["og"] = base["og"]
        elif out := handle("og", lambda f: save_cropped(f, "og")):
            fotos["og"] = out["src"]

        # galeria: mantém só imagens que já existiam (evita caminhos arbitrários)
        known = {g["src"]: g for g in site["fotos"]["galeria"]} | {g["src"]: g for g in base["galeria"]}
        gallery = []
        idxs = sorted({int(m.group(1)) for k in request.form if (m := re.match(r"^g:(\d+):src$", k))})
        for i in idxs:
            src = request.form.get(f"g:{i}:src", "")
            if src not in known or request.form.get(f"g:{i}:remover"):
                continue
            item = dict(known[src])
            item["alt"] = request.form.get(f"g:{i}:alt", "").strip()[:200] or item.get("alt", "")
            gallery.append(item)
        for f in request.files.getlist("galeria_novas"):
            if not f or not f.filename:
                continue
            if len(gallery) >= MAX_GALLERY:
                errors.append(f"A galeria aceita no máximo {MAX_GALLERY} fotos.")
                break
            try:
                out = save_gallery(f)
            except ImageError as exc:
                errors.append(f"{f.filename}: {exc}")
                continue
            gallery.append({**out, "alt": "Foto institucional: Jaqueline Sias Despachante", "pos": ""})
        fotos["galeria"] = gallery

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("admin/fotos.html", fotos=fotos, slots=PHOTO_SLOTS, max_gallery=MAX_GALLERY), 400
        store().save([(("fotos",), fotos)])
        invalidate()
        flash("Fotos salvas. Já estão no site.", "ok")
        return redirect(url_for("admin.photos"))
    return render_template("admin/fotos.html", fotos=fotos, slots=PHOTO_SLOTS, max_gallery=MAX_GALLERY)


@bp.post("/fotos/restaurar")
def reset_photos():
    if store().reset([("fotos",)]):
        flash("Fotos originais restauradas. Um backup foi salvo.", "ok")
    invalidate()
    return redirect(url_for("admin.photos"))


# =========================================================================== backup e reset
@bp.get("/backup")
def backup():
    return render_template("admin/backup.html", backups=store().list_backups())


@bp.post("/restaurar-tudo")
def reset_all():
    if request.form.get("confirmacao", "").strip().upper() != "RESTAURAR":
        flash("Digite RESTAURAR para confirmar.", "error")
        return redirect(url_for("admin.backup"))
    if store().reset(None):
        log.warning("Painel: todas as configurações restauradas ao padrão")
        flash("O site voltou ao conteúdo original. Um backup foi salvo — você pode desfazer abaixo.", "ok")
    else:
        flash("O site já está com o conteúdo original.", "ok")
    invalidate()
    return redirect(url_for("admin.backup"))


@bp.post("/backup/restaurar")
def restore_backup():
    if store().restore_backup(request.form.get("nome", "")):
        flash("Backup restaurado.", "ok")
    else:
        flash("Backup não encontrado.", "error")
    invalidate()
    return redirect(url_for("admin.backup"))


@bp.get("/backup/exportar")
def export_settings():
    body = json.dumps(store().overrides(), ensure_ascii=False, indent=2)
    name = f"site-jaqueline-configuracoes-{datetime.now():%Y%m%d-%H%M}.json"
    return Response(body, mimetype="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


@bp.post("/backup/importar")
def import_settings():
    f = request.files.get("arquivo")
    try:
        data = json.loads(f.read(2_000_001).decode("utf-8")) if f else None
    except (ValueError, UnicodeDecodeError):
        data = None
    base = defaults()
    valid = isinstance(data, dict) and all(
        k in base and type(v) is type(base[k]) for k, v in data.items()
    )
    if not valid:
        flash("Arquivo inválido. Use um arquivo exportado por este painel.", "error")
    else:
        store().replace_all(data)
        invalidate()
        flash("Configurações importadas. A versão anterior foi salva como backup.", "ok")
    return redirect(url_for("admin.backup"))


# =========================================================================== verificação de SEO
def seo_checks(site: dict) -> list[dict]:
    """Diagnóstico simples de SEO e configuração, exibido no painel."""
    out = []

    def add(level, msg, page=None):
        out.append({"level": level, "msg": msg, "page": page})

    cfg = current_app.config
    seo = site["seo"]
    if seo["bloquear_indexacao"]:
        add("erro", "O site está escondido do Google (noindex). Desative em SEO → Verificação e indexação.", "seo")
    if "localhost" in cfg["SITE_URL"] or "seudominio" in cfg["SITE_URL"]:
        add("aviso", "SITE_URL ainda não aponta para o domínio definitivo (ajuste no .env do servidor).")
    titles = {}
    for key, p in seo["paginas"].items():
        t, d = p["titulo"], p["descricao"]
        if not 30 <= len(t) <= 60:
            add("aviso", f"Título da página \"{key}\" tem {len(t)} caracteres (ideal: 30 a 60).", "seo")
        if not 70 <= len(d) <= 160:
            add("aviso", f"Descrição da página \"{key}\" tem {len(d)} caracteres (ideal: 70 a 160).", "seo")
        titles.setdefault(t, []).append(key)
    for t, keys in titles.items():
        if len(keys) > 1:
            add("erro", f"Páginas {', '.join(keys)} têm o mesmo título. Cada página precisa de um título único.", "seo")
    if not seo["google_verificacao"]:
        add("dica", "Cadastre o site no Google Search Console e cole o código de verificação em SEO.", "seo")
    if not seo["areas_atendidas"].strip():
        add("dica", "Informe as cidades/bairros atendidos para melhorar a busca local.", "seo")
    c = site["contato"]
    if not c["whatsapp"]:
        add("aviso", "Número do WhatsApp vazio: os botões de WhatsApp estão escondidos.", "contato")
    if not c["google_avaliacoes_url"]:
        add("dica", "Adicione o link do Perfil da Empresa no Google para o botão \"Ver no Google\".", "contato")
    if not c["endereco"] and not c["cidade"]:
        add("dica", "Informe ao menos a cidade: ela aparece nos dados de negócio local.", "contato")
    f = site["fotos"]
    if any(not g.get("alt") for g in f["galeria"]):
        add("aviso", "Há fotos da galeria sem descrição (texto alternativo).", None)
    if len(site["faq"]) < 3:
        add("dica", "Ter ao menos 3 perguntas frequentes ajuda o Google a exibir respostas do seu site.", "conteudos")
    visible_reviews = sum(1 for r in site["avaliacoes"] if r["visivel"])
    if visible_reviews == 0 and site["aparencia"]["secoes"]["avaliacoes"]:
        add("aviso", "Nenhuma avaliação visível: a seção de avaliações ficará vazia.", "avaliacoes")
    p = site["pixels"]
    if tracking_enabled(site) and not p["pedir_consentimento"]:
        add("aviso", "Pixels ativos sem aviso de cookies. Pela LGPD, o recomendado é pedir consentimento.", "pixels")
    if p["gtm"] and (p["ga4"] or p["meta"]):
        add("dica", "Tag Manager e pixels diretos ativos ao mesmo tempo: confira se não há contagem dupla.", "pixels")
    return out
