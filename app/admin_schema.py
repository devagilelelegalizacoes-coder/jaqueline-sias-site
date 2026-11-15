"""Definição dos campos editáveis em cada aba do painel /admin.

Cada aba tem "blocos": um grupo de campos (`fields`) gravado em um caminho das
configurações, ou uma lista de itens (`list`) que pode ganhar/perder itens.
"""

ICONS = {
    "arrow-left-right": "Setas (transferência)",
    "car-front": "Carro",
    "calendar-check": "Calendário",
    "file-check": "Documento aprovado",
    "file-text": "Documento",
    "search": "Lupa (consulta)",
    "copy": "Cópia / segunda via",
    "settings-2": "Ajustes",
    "user-round-check": "Pessoa",
    "message-circle": "Mensagem",
    "compass": "Bússola",
    "smartphone": "Celular",
    "list-checks": "Lista de tarefas",
    "clipboard-list": "Prancheta",
    "scale": "Balança (legislação)",
    "shield-check": "Escudo (segurança)",
    "map-pin": "Localização",
    "phone": "Telefone",
    "mail": "E-mail",
    "check": "Visto",
    "whatsapp": "WhatsApp",
    "instagram": "Instagram",
}

DIFF_STYLES = {
    "feature": "Destaque grande (fundo claro com monograma)",
    "dark": "Roxo escuro",
    "light": "Claro",
    "wide": "Largo (ocupa a linha inteira)",
}

PIXEL_PATTERNS = {
    "ga4": (r"G-[A-Z0-9]{4,12}", "G-XXXXXXXXXX"),
    "gtm": (r"GTM-[A-Z0-9]{4,10}", "GTM-XXXXXXX"),
    "google_ads": (r"AW-\d{6,12}", "AW-123456789"),
    "google_ads_rotulo": (r"[A-Za-z0-9_-]{4,40}", "AbCdEfGhIjk"),
    "meta": (r"\d{10,20}", "123456789012345"),
    "tiktok": (r"[A-Z0-9]{10,30}", "C1A2B3C4D5E6F7G8H9"),
    "clarity": (r"[a-z0-9]{6,16}", "abcd1234ef"),
}


def F(key, label, type="text", **kw):
    return {"key": key, "label": label, "type": type, **kw}


def fields_block(path, title, fields, **kw):
    return {"kind": "fields", "path": tuple(path), "id": ".".join(path), "title": title, "fields": fields, **kw}


def list_block(path, title, item_label, fields, **kw):
    return {"kind": "list", "path": (path,), "id": path, "title": title, "item_label": item_label,
            "fields": fields, **kw}


def _t(key, label, maxlength=160, **kw):
    return F(key, label, "text", maxlength=maxlength, **kw)


def _ta(key, label, maxlength=600, rows=3, **kw):
    return F(key, label, "textarea", maxlength=maxlength, rows=rows, **kw)


def _section_texts(group, title, extra=()):
    base = [_t("chamada", "Texto pequeno acima do título", 60), _t("titulo", "Título da seção", 120)]
    return fields_block(("textos", group), title, base + list(extra))


PAGES = {
    "contato": {
        "title": "Contato e WhatsApp",
        "icon": "phone",
        "intro": "Número do WhatsApp, telefone, e-mail, redes sociais e endereço. Campos vazios não aparecem no site.",
        "blocks": [
            fields_block(("contato",), "WhatsApp e telefone", [
                F("whatsapp", "Número do WhatsApp", "whatsapp", placeholder="(21) 97260-2420",
                  help="Com DDD. Todos os botões de WhatsApp do site usam este número. Deixe vazio para esconder os botões."),
                _ta("whatsapp_mensagem", "Mensagem que já vem escrita ao clicar no WhatsApp", 300, 2),
                F("telefone", "Outro telefone (opcional)", "phone", placeholder="(21) 3333-4444",
                  help="Telefone fixo ou outro celular. Aparece no rodapé e na seção de contato."),
            ]),
            fields_block(("contato",), "E-mail e redes sociais", [
                F("email", "E-mail de contato", "email", maxlength=120),
                F("instagram_url", "Link do Instagram", "url", placeholder="https://www.instagram.com/...",
                  help="Deixe vazio para esconder a seção do Instagram."),
                _t("instagram_usuario", "Nome de usuário no Instagram", 60, placeholder="@usuario"),
                F("google_avaliacoes_url", "Link do perfil no Google (avaliações)", "url",
                  help="Abra seu Perfil da Empresa no Google, clique em \"Compartilhar\" e cole o link aqui."),
            ]),
            fields_block(("contato",), "Endereço e horário", [
                _t("cidade", "Cidade", 60),
                F("estado", "Estado (UF)", "uf", maxlength=2, placeholder="RJ"),
                _t("endereco", "Endereço (rua, número, bairro)", 160, help="Só preencha se o endereço for público."),
                _t("cep", "CEP", 9, placeholder="24000-000"),
                _t("horario", "Horário de atendimento", 120, placeholder="Seg. a sex., 9h às 18h"),
                F("mapa_url", "Mapa do Google (link de incorporação)", "maps",
                  help="No Google Maps: Compartilhar → Incorporar um mapa → copie só o endereço que está dentro de src=\"...\"."),
            ]),
        ],
    },
    "textos": {
        "title": "Textos do site",
        "icon": "file-text",
        "intro": "Títulos, chamadas e botões de cada parte do site. Os textos de serviços, diferenciais, avaliações e dúvidas ficam nas abas próprias.",
        "blocks": [
            fields_block(("textos", "hero"), "Topo da página inicial", [
                _t("chamada", "Texto pequeno acima do título", 80),
                _t("titulo", "Título principal (H1)", 90, count=(20, 70)),
                _ta("subtitulo", "Texto abaixo do título", 300, 2),
                _t("botao_principal", "Botão do WhatsApp", 50),
                _t("botao_secundario", "Botão de serviços", 50),
            ]),
            fields_block(("textos", "sobre"), "Seção Sobre", [
                _t("chamada", "Texto pequeno acima do título", 60),
                _t("titulo", "Título", 120),
                _ta("texto", "Texto (deixe uma linha em branco entre parágrafos)", 3000, 9),
                _t("botao", "Botão", 50),
            ]),
            fields_block(("textos", "instagram"), "Seção Instagram", [
                _t("titulo", "Título", 120), _t("botao", "Botão", 50), _ta("nota", "Observação abaixo das fotos", 300, 2),
            ]),
            fields_block(("textos", "contato"), "Seção de contato e formulário", [
                _t("chamada", "Texto pequeno acima do título", 60),
                _t("titulo", "Título", 120),
                _t("botao_whatsapp", "Botão do WhatsApp", 50),
                _t("form_titulo", "Título do formulário", 80),
                _t("form_aviso", "Aviso do formulário", 120),
                _t("form_botao", "Botão de enviar", 40),
                _t("sucesso_titulo", "Título após o envio", 80),
                _ta("sucesso_texto", "Texto após o envio", 300, 2),
            ]),
            fields_block(("textos", "paginas"), "Topo das páginas internas", [
                _t("servicos_titulo", "Página Serviços: título", 120), _ta("servicos_texto", "Página Serviços: texto", 300, 2),
                _t("sobre_titulo", "Página Sobre: título", 120), _ta("sobre_texto", "Página Sobre: texto", 300, 2),
                _t("contato_titulo", "Página Contato: título", 120), _ta("contato_texto", "Página Contato: texto", 300, 2),
                _t("conteudo_titulo", "Página Conteúdo: título", 120), _ta("conteudo_texto", "Página Conteúdo: texto", 300, 2),
            ]),
            fields_block(("textos", "geral"), "Menu, rodapé e botão flutuante", [
                _t("header_cta", "Botão do menu (computador)", 40),
                _t("menu_cta", "Botão do menu (celular)", 50),
                _t("wa_tooltip", "Balão do botão flutuante do WhatsApp", 60),
                _ta("rodape_sobre", "Rodapé: frase sobre a empresa", 300, 2),
                _ta("rodape_privacidade", "Rodapé: aviso de privacidade", 300, 2),
                _t("copyright", "Rodapé: direitos autorais (após © ano)", 120),
            ]),
        ],
    },
    "servicos": {
        "title": "Serviços",
        "icon": "car-front",
        "intro": "Inclua, edite, reordene ou remova serviços. Cada serviço ganha um botão de WhatsApp com mensagem própria e aparece no formulário de contato.",
        "blocks": [
            _section_texts("servicos", "Títulos da seção", [
                _ta("intro", "Texto ao lado do título", 300, 2),
                _t("botao_card", "Texto do link em cada serviço", 40),
                _ta("mensagem_whatsapp", "Mensagem do WhatsApp por serviço", 300, 2,
                    help="Use {servico} onde deve entrar o nome do serviço."),
            ]),
            list_block("servicos", "Lista de serviços", "Serviço", [
                F("nome", "Nome do serviço", "text", maxlength=80, required=True),
                F("icone", "Ícone", "icon"),
                _ta("descricao", "Descrição curta", 300, 2),
            ], max_items=24),
        ],
    },
    "diferenciais": {
        "title": "Diferenciais",
        "icon": "user-round-check",
        "intro": "Os cartões da seção \"Por que escolher\". O layout foi desenhado para 5 cartões; com outra quantidade eles se reorganizam automaticamente.",
        "blocks": [
            _section_texts("diferenciais", "Títulos da seção"),
            list_block("diferenciais", "Cartões", "Diferencial", [
                F("titulo", "Título", "text", maxlength=80, required=True),
                F("icone", "Ícone", "icon"),
                F("estilo", "Estilo do cartão", "select", options=DIFF_STYLES),
                _ta("descricao", "Descrição", 300, 2),
            ], max_items=12),
        ],
    },
    "avaliacoes": {
        "title": "Avaliações do Google",
        "icon": "message-circle",
        "intro": "Copie as avaliações do seu Perfil da Empresa no Google. Desmarque \"Mostrar no site\" para esconder uma avaliação sem apagá-la.",
        "blocks": [
            _section_texts("avaliacoes", "Títulos da seção", [
                _ta("intro", "Texto ao lado do título", 300, 2),
                _t("origem", "Legenda abaixo do nome", 60),
                _t("botao_google", "Botão para o Google", 40),
            ]),
            list_block("avaliacoes", "Avaliações", "Avaliação", [
                F("nome", "Nome do cliente", "text", maxlength=80, required=True),
                F("visivel", "Mostrar no site", "bool", default=True),
                _ta("texto", "Texto da avaliação", 1500, 3),
            ], max_items=80),
        ],
    },
    "conteudos": {
        "title": "Como funciona, FAQ e temas",
        "icon": "list-checks",
        "intro": "Passos do atendimento, perguntas frequentes (também enviadas ao Google como dados estruturados) e temas da seção de conteúdo.",
        "blocks": [
            _section_texts("como_funciona", "Como funciona: títulos"),
            list_block("passos", "Passos", "Passo", [
                F("titulo", "Título do passo", "text", maxlength=120, required=True),
                _ta("descricao", "Descrição", 300, 2),
            ], max_items=8),
            _section_texts("faq", "Dúvidas frequentes: títulos", [
                _t("intro", "Frase antes do link", 80), _t("link", "Texto do link para o WhatsApp", 80),
            ]),
            list_block("faq", "Perguntas e respostas", "Pergunta", [
                F("pergunta", "Pergunta", "text", maxlength=200, required=True),
                _ta("resposta", "Resposta", 2000, 4),
            ], max_items=40),
            _section_texts("conteudo", "Conteúdo: títulos", [
                _ta("intro", "Texto (sem artigos publicados)", 300, 2),
                _ta("intro_com_artigos", "Texto (com artigos publicados)", 300, 2),
                _t("selo", "Selo dos temas", 30),
            ]),
            list_block("temas", "Temas", "Tema", [
                F("titulo", "Título", "text", maxlength=80, required=True),
                F("icone", "Ícone", "icon"),
                _ta("descricao", "Descrição", 300, 2),
            ], max_items=12),
        ],
    },
    "seo": {
        "title": "SEO (Google)",
        "icon": "search",
        "intro": "Como o site aparece no Google e ao ser compartilhado. Títulos com até 60 caracteres e descrições entre 70 e 160 caracteres têm melhor exibição.",
        "blocks": [
            *[
                fields_block(("seo", "paginas", key), f"Página: {label}", [
                    _t("titulo", "Título no Google (title)", 90, count=(30, 60), snippet=url),
                    _ta("descricao", "Descrição no Google (meta description)", 300, 3, count=(70, 160)),
                ])
                for key, label, url in [
                    ("index", "Início", "/"), ("servicos", "Serviços", "/servicos"), ("sobre", "Sobre", "/sobre"),
                    ("contato", "Contato", "/contato"), ("conteudo", "Conteúdo", "/conteudo"),
                    ("privacidade", "Privacidade", "/privacidade"),
                ]
            ],
            fields_block(("seo",), "Negócio local (dados estruturados Schema.org)", [
                _ta("descricao_negocio", "Descrição do negócio", 300, 2,
                    help="Usada nos dados estruturados que o Google lê para entender o negócio."),
                _t("responsavel", "Nome da responsável", 80),
                _ta("areas_atendidas", "Cidades ou bairros atendidos (um por linha)", 1000, 4,
                    help="Ajuda a aparecer em buscas locais, como \"despachante em Niterói\"."),
            ]),
            fields_block(("seo",), "Verificação e indexação", [
                F("google_verificacao", "Código do Google Search Console", "verification",
                  help="Search Console → Adicionar propriedade → Prefixo do URL → Tag HTML. Pode colar a tag inteira."),
                F("bing_verificacao", "Código do Bing Webmaster Tools", "verification"),
                F("facebook_verificacao", "Verificação de domínio da Meta (Facebook)", "verification",
                  help="Gerenciador de Negócios → Segurança da marca → Domínios → Meta tag."),
                F("bloquear_indexacao", "Esconder o site do Google (noindex) — use só durante testes", "bool"),
            ]),
        ],
    },
    "pixels": {
        "title": "Pixels e rastreamento",
        "icon": "settings-2",
        "intro": "Cole apenas o ID de cada ferramenta; o site instala o código. Cliques no WhatsApp e envios do formulário são registrados automaticamente como conversões.",
        "blocks": [
            fields_block(("pixels",), "Google", [
                F("ga4", "Google Analytics 4 — ID de medição", "pixel", placeholder="G-XXXXXXXXXX"),
                F("google_ads", "Google Ads — ID da conta (tag)", "pixel", placeholder="AW-123456789"),
                F("google_ads_rotulo", "Google Ads — rótulo da conversão de contato (opcional)", "pixel",
                  help="Google Ads → Metas → Conversões → Configuração da tag → parte depois da barra em send_to."),
                F("gtm", "Google Tag Manager — ID do contêiner", "pixel", placeholder="GTM-XXXXXXX",
                  help="Use o Tag Manager OU os campos acima, não os dois para a mesma ferramenta (evita contagem dupla)."),
            ]),
            fields_block(("pixels",), "Redes sociais e análise", [
                F("meta", "Pixel da Meta (Facebook/Instagram) — ID", "pixel", placeholder="123456789012345"),
                F("tiktok", "Pixel do TikTok — ID", "pixel", placeholder="C1A2B3C4D5E6F7G8H9"),
                F("clarity", "Microsoft Clarity — ID do projeto", "pixel", placeholder="abcd1234ef",
                  help="Mapas de calor e gravações de sessão, gratuito."),
            ]),
            fields_block(("pixels",), "Privacidade (LGPD)", [
                F("pedir_consentimento", "Mostrar aviso de cookies e só ativar os pixels após o visitante aceitar (recomendado)", "bool"),
            ]),
            fields_block(("pixels",), "Código personalizado (avançado)", [
                F("codigo_head", "Código extra no <head>", "code", rows=5, maxlength=20000,
                  help="Para ferramentas sem campo acima. Atenção: código personalizado reduz a proteção de segurança (CSP) do site."),
                F("codigo_body", "Código extra no fim do <body>", "code", rows=5, maxlength=20000),
            ]),
        ],
    },
    "aparencia": {
        "title": "Aparência e seções",
        "icon": "compass",
        "intro": "Escolha quais seções aparecem e ajuste as cores da marca.",
        "blocks": [
            fields_block(("aparencia", "secoes"), "Seções visíveis", "SECTIONS"),
            fields_block(("aparencia",), "Avaliações", [
                F("avaliacoes_iniciais", "Quantas avaliações mostrar antes do botão \"Ver todas\"", "int", min=1, max=30),
            ]),
            fields_block(("aparencia", "cores"), "Cores da marca", [
                F("purple", "Roxo principal", "color"),
                F("purple_deep", "Roxo escuro (fundos)", "color"),
                F("purple_night", "Roxo noite (fundos mais escuros)", "color"),
                F("gold", "Dourado", "color"),
                F("gold_light", "Dourado claro", "color"),
                F("gold_dark", "Dourado escuro", "color"),
            ]),
        ],
    },
}


def resolve_pages(sections):
    """Preenche os campos de visibilidade das seções (dependem da lista SECTIONS)."""
    for block in PAGES["aparencia"]["blocks"]:
        if block["fields"] == "SECTIONS":
            block["fields"] = [F(key, label, "bool") for key, label in sections]
    return PAGES
