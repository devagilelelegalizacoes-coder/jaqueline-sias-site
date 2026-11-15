"""Configurações do site editáveis pelo painel /admin.

Os valores padrão vêm de `content.py` e do `.env`. O painel grava somente o que
foi alterado em `instance/site_settings.json`; "Restaurar padrão" apaga essas
alterações (com backup automático). Funciona com vários workers do Gunicorn:
cada processo relê o arquivo quando a data de modificação muda.
"""
import copy
import json
import os
import re
import tempfile
import threading
import unicodedata
from datetime import datetime
from pathlib import Path

from flask import current_app, g

from . import content

MAX_BACKUPS = 15

# Seções da página (ordem da home) que podem ser ocultadas no painel.
SECTIONS = [
    ("sobre", "Sobre"),
    ("servicos", "Serviços"),
    ("diferenciais", "Diferenciais"),
    ("avaliacoes", "Avaliações do Google"),
    ("como_funciona", "Como funciona"),
    ("faq", "Dúvidas frequentes"),
    ("conteudo", "Conteúdo"),
    ("instagram", "Instagram"),
    ("contato", "Contato / formulário"),
]

DEFAULT_COLORS = {
    "purple": "#4D0D63",
    "purple_deep": "#3E0A4F",
    "purple_night": "#2A0636",
    "gold": "#D4AF6A",
    "gold_light": "#F3D98B",
    "gold_dark": "#B8893B",
}


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "item"


# --------------------------------------------------------------------------- padrões
def build_defaults(cfg) -> dict:
    city, state = cfg["BUSINESS_CITY"], cfg["BUSINESS_STATE"]
    loc = ", ".join(p for p in (city, state) if p)
    em_loc = f" em {loc}" if loc else ""
    if city:
        onde = f", {'no Rio de Janeiro' if state == 'RJ' else state}" if state else ""
        atendo = f"Atendo em {city}{onde}, e estou a uma mensagem de distância pelo WhatsApp."
    else:
        atendo = "Estou a uma mensagem de distância pelo WhatsApp."

    return {
        "contato": {
            "whatsapp": cfg["WHATSAPP_NUMBER"],
            "whatsapp_mensagem": cfg["WHATSAPP_DEFAULT_MESSAGE"],
            "telefone": "",
            "email": cfg["CONTACT_EMAIL"],
            "instagram_url": cfg["INSTAGRAM_URL"],
            "instagram_usuario": cfg["INSTAGRAM_HANDLE"],
            "cidade": city,
            "estado": state,
            "endereco": cfg["BUSINESS_ADDRESS"],
            "cep": cfg["BUSINESS_POSTAL_CODE"],
            "horario": cfg["BUSINESS_HOURS"],
            "mapa_url": cfg["MAPS_EMBED_URL"],
            "google_avaliacoes_url": cfg["GOOGLE_REVIEWS_URL"],
        },
        "textos": {
            "geral": {
                "header_cta": "Fale comigo",
                "menu_cta": "Fale comigo pelo WhatsApp",
                "wa_tooltip": "Fale diretamente comigo",
                "rodape_sobre": f"Assessoria em serviços e documentação veicular{em_loc}.",
                "rodape_privacidade": "Os dados do formulário são usados apenas para responder ao seu contato.",
                "copyright": "Jaqueline Sias Despachante. Todos os direitos reservados.",
            },
            "hero": {
                "chamada": f"Despachante{' · ' + loc if loc else ''}",
                "titulo": "Seu veículo em dia, sem complicação.",
                "subtitulo": "Assessoria em serviços e documentação veicular com atendimento personalizado, praticidade e confiança.",
                "botao_principal": "Fale comigo pelo WhatsApp",
                "botao_secundario": "Conheça nossos serviços",
            },
            "sobre": {
                "chamada": "Sobre",
                "titulo": "Prazer, sou Jaqueline Sias.",
                "texto": (
                    "Acredito que cuidar da documentação de um veículo vai além de preencher formulários. "
                    "Cada processo envolve um patrimônio, prazos a cumprir e, muitas vezes, a tranquilidade "
                    "de uma família ou de um negócio.\n\n"
                    "Por isso, meu atendimento é próximo e individual: escuto a sua necessidade, explico cada "
                    "etapa com clareza e conduzo a documentação com responsabilidade, do primeiro contato à "
                    "conclusão do processo.\n\n" + atendo
                ),
                "botao": "Conversar com a Jaqueline",
            },
            "servicos": {
                "chamada": "Serviços",
                "titulo": "Documentação veicular com quem cuida de perto.",
                "intro": "Escolha o serviço e envie uma mensagem. Você recebe a orientação sobre documentos e próximos passos para o seu caso.",
                "botao_card": "Solicitar atendimento",
                "mensagem_whatsapp": "Olá, Jaqueline! Acessei seu site e gostaria de informações sobre o serviço de {servico}.",
            },
            "diferenciais": {
                "chamada": "Diferenciais",
                "titulo": "Por que escolher a Jaqueline?",
            },
            "avaliacoes": {
                "chamada": "Avaliações no Google",
                "titulo": "O que dizem os clientes.",
                "intro": "Relatos publicados por clientes no perfil da Jaqueline Sias Despachante no Google.",
                "origem": "Avaliação no Google",
                "botao_google": "Ver no Google",
            },
            "como_funciona": {
                "chamada": "Como funciona",
                "titulo": "Três passos para começar.",
            },
            "faq": {
                "chamada": "Dúvidas frequentes",
                "titulo": "Perguntas que recebo com frequência.",
                "intro": "Não encontrou a sua?",
                "link": "Mande sua pergunta pelo WhatsApp",
            },
            "conteudo": {
                "chamada": "Conteúdo",
                "titulo": "Informação que facilita sua vida.",
                "intro": "Artigos e orientações sobre documentação veicular em preparação.",
                "intro_com_artigos": "Orientações sobre documentação veicular, legislação e processos.",
                "selo": "Em breve",
            },
            "instagram": {
                "titulo": "Acompanhe nossas dicas e novidades.",
                "botao": "Visitar o Instagram",
                "nota": "Materiais institucionais da marca. As publicações recentes estão no perfil oficial.",
            },
            "contato": {
                "chamada": "Contato",
                "titulo": "Vamos resolver a documentação do seu veículo?",
                "botao_whatsapp": "Fale comigo pelo WhatsApp",
                "form_titulo": "Envie uma mensagem",
                "form_aviso": "Campos com * são obrigatórios.",
                "form_botao": "Enviar mensagem",
                "sucesso_titulo": "Mensagem recebida",
                "sucesso_texto": "Obrigada pelo contato. Retorno pelo telefone informado assim que possível.",
            },
            "paginas": {
                "servicos_titulo": "Serviços de despachante veicular",
                "servicos_texto": "Transferência, emplacamento, licenciamento e regularização de documentos, com orientação do início ao fim do processo.",
                "sobre_titulo": "Sobre a Jaqueline Sias",
                "sobre_texto": "Atendimento próximo, comunicação transparente e documentação conduzida com responsabilidade.",
                "contato_titulo": "Fale com a Jaqueline",
                "contato_texto": "Envie sua dúvida ou solicitação. O WhatsApp é o caminho mais rápido.",
                "conteudo_titulo": "Conteúdo e informação",
                "conteudo_texto": "Orientações sobre documentação veicular, legislação, cuidados com o veículo e processos administrativos.",
            },
        },
        "servicos": [
            {"nome": s["name"], "icone": s["icon"], "descricao": s["desc"]} for s in content.SERVICES
        ],
        "diferenciais": [
            {"icone": d["icon"], "titulo": d["title"], "descricao": d["desc"], "estilo": d["variant"]}
            for d in content.DIFFERENTIALS
        ],
        "avaliacoes": [
            {"nome": r["name"], "texto": r["text"], "visivel": True} for r in content.REVIEWS
        ],
        "passos": [{"titulo": s["title"], "descricao": s["desc"]} for s in content.STEPS],
        "faq": [{"pergunta": f["q"], "resposta": f["a"]} for f in content.FAQS],
        "temas": [
            {"icone": t["icon"], "titulo": t["title"], "descricao": t["desc"]} for t in content.TOPICS
        ],
        "fotos": {
            "hero": "images/team/jaqueline-hero.webp",
            "hero_pequena": "images/team/jaqueline-hero-480.webp",
            "hero_alt": "Jaqueline Sias, despachante, sorrindo e segurando um celular",
            "sobre": "images/team/jaqueline-sobre.webp",
            "sobre_pequena": "images/team/jaqueline-sobre-540.webp",
            "sobre_alt": "Retrato de Jaqueline Sias com blusa branca e calça roxa",
            "logo": "images/branding/logo-horizontal.webp",
            "logo_png": "images/branding/logo-horizontal.png",
            "logo_largura": 148,
            "logo_altura": 44,
            "og": "images/branding/og-image.jpg",
            "galeria": [
                {"src": g["src"], "alt": g["alt"], "w": g["w"], "h": g["h"], "pos": g.get("pos", "")}
                for g in content.INSTAGRAM_GALLERY
            ],
        },
        "seo": {
            "paginas": {
                "index": {
                    "titulo": f"Jaqueline Sias Despachante · Documentação veicular{em_loc}",
                    "descricao": f"Despachante veicular{em_loc}: transferência, licenciamento, primeiro emplacamento e regularização de documentos com atendimento personalizado. Fale pelo WhatsApp.",
                },
                "servicos": {
                    "titulo": f"Serviços de despachante veicular{em_loc} · Jaqueline Sias",
                    "descricao": "Transferência de propriedade, primeiro emplacamento, licenciamento, regularização documental, consulta de débitos, segunda via e alteração de características.",
                },
                "sobre": {
                    "titulo": "Sobre Jaqueline Sias · Despachante",
                    "descricao": "Conheça Jaqueline Sias: atendimento próximo, comunicação transparente e documentação veicular conduzida com responsabilidade.",
                },
                "contato": {
                    "titulo": "Contato · Jaqueline Sias Despachante",
                    "descricao": "Vamos resolver a documentação do seu veículo? Fale com Jaqueline Sias pelo WhatsApp ou envie uma mensagem pelo formulário.",
                },
                "conteudo": {
                    "titulo": "Informação que facilita sua vida · Jaqueline Sias Despachante",
                    "descricao": "Orientações sobre documentação veicular, legislação de trânsito, cuidados com o veículo e processos administrativos.",
                },
                "privacidade": {
                    "titulo": "Política de Privacidade · Jaqueline Sias Despachante",
                    "descricao": "Como os dados enviados pelo site da Jaqueline Sias Despachante são coletados, usados e protegidos, conforme a LGPD.",
                },
            },
            "descricao_negocio": "Assessoria em serviços e documentação veicular com atendimento personalizado, praticidade e confiança.",
            "responsavel": "Jaqueline Sias",
            "areas_atendidas": city,
            "google_verificacao": cfg["GOOGLE_SITE_VERIFICATION"],
            "bing_verificacao": "",
            "facebook_verificacao": "",
            "bloquear_indexacao": False,
        },
        "pixels": {
            "ga4": "",
            "gtm": "",
            "google_ads": "",
            "google_ads_rotulo": "",
            "meta": "",
            "tiktok": "",
            "clarity": "",
            "pedir_consentimento": True,
            "codigo_head": "",
            "codigo_body": "",
        },
        "aparencia": {
            "secoes": {key: True for key, _ in SECTIONS},
            "avaliacoes_iniciais": 6,
            "cores": dict(DEFAULT_COLORS),
        },
    }


def _pop_path(data: dict, path: tuple) -> None:
    """Remove data[path...] e apaga dicionários que ficarem vazios."""
    parents = []
    node = data
    for key in path[:-1]:
        if not isinstance(node.get(key), dict):
            return
        parents.append((node, key))
        node = node[key]
    node.pop(path[-1], None)
    for parent, key in reversed(parents):
        if parent[key]:
            break
        parent.pop(key)


def deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


# --------------------------------------------------------------------------- armazenamento
class SettingsStore:
    """Guarda as alterações feitas no painel (JSON em disco ou memória, nos testes)."""

    def __init__(self, path: str | None):
        self.path = Path(path) if path else None
        self._lock = threading.Lock()
        self._cache_key = None
        self._cache: dict = {}
        self._mem: dict = {}
        self._mem_backups: list[tuple[str, dict]] = []

    # leitura -------------------------------------------------------------
    def overrides(self) -> dict:
        if self.path is None:
            return copy.deepcopy(self._mem)
        try:
            st = self.path.stat()
        except FileNotFoundError:
            return {}
        key = (st.st_mtime_ns, st.st_size)
        if key != self._cache_key:
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                current_app.logger.exception("Arquivo de configurações inválido: %s", self.path)
                data = {}
            self._cache, self._cache_key = (data if isinstance(data, dict) else {}), key
        return copy.deepcopy(self._cache)

    # escrita -------------------------------------------------------------
    def _write(self, data: dict) -> None:
        if self.path is None:
            self._mem = copy.deepcopy(data)
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".settings-", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        self._cache_key = None

    def save(self, changes: list[tuple[tuple, object]]) -> None:
        """Grava valores em caminhos (ex.: ("textos", "hero")). Dicionários são mesclados;
        listas e valores simples substituem o que havia."""
        with self._lock:
            data = self.overrides()
            for path, value in changes:
                node = data
                for key in path[:-1]:
                    node = node.setdefault(key, {})
                last = path[-1]
                if isinstance(value, dict) and isinstance(node.get(last), dict):
                    node[last].update(value)
                else:
                    node[last] = value
            self._write(data)

    def reset(self, paths: list[tuple] | None = None) -> bool:
        """Volta ao padrão os caminhos indicados (ou tudo). Faz backup antes."""
        with self._lock:
            data = self.overrides()
            if not data:
                return False
            new = {} if paths is None else copy.deepcopy(data)
            for path in paths or ():
                _pop_path(new, path)
            if new == data:
                return False
            self.backup(data, "antes-de-restaurar")
            self._write(new)
            return True

    def replace_all(self, data: dict) -> None:
        with self._lock:
            current = self.overrides()
            if current:
                self.backup(current, "antes-de-importar")
            self._write(data)

    # backups -------------------------------------------------------------
    @property
    def backup_dir(self) -> Path | None:
        return self.path.parent / "backups" if self.path else None

    def backup(self, data: dict, reason: str) -> None:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        name = f"configuracoes-{stamp}-{reason}.json"
        if self.path is None:
            self._mem_backups.append((name, copy.deepcopy(data)))
            del self._mem_backups[:-MAX_BACKUPS]
            return
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        (self.backup_dir / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        for old in self.list_backups()[MAX_BACKUPS:]:
            (self.backup_dir / old).unlink(missing_ok=True)

    def list_backups(self) -> list[str]:
        if self.path is None:
            return [n for n, _ in reversed(self._mem_backups)]
        if not self.backup_dir.exists():
            return []
        return sorted((p.name for p in self.backup_dir.glob("configuracoes-*.json")), reverse=True)

    def restore_backup(self, name: str) -> bool:
        if name not in self.list_backups():
            return False
        if self.path is None:
            data = dict(self._mem_backups)[name]
        else:
            data = json.loads((self.backup_dir / name).read_text(encoding="utf-8"))
        self.replace_all(data)
        return True


# --------------------------------------------------------------------------- acesso
def store() -> SettingsStore:
    return current_app.extensions["settings_store"]


def defaults() -> dict:
    return build_defaults(current_app.config)


def get_settings() -> dict:
    """Configurações efetivas (padrão + alterações do painel), em cache por requisição."""
    cached = g.get("_site_settings")
    if cached is None:
        cached = deep_merge(defaults(), store().overrides())
        g._site_settings = cached
    return cached


def invalidate() -> None:
    g.pop("_site_settings", None)


def tracking_enabled(site: dict) -> bool:
    p = site["pixels"]
    return any(p[k] for k in ("ga4", "gtm", "google_ads", "meta", "tiktok", "clarity", "codigo_head", "codigo_body"))
