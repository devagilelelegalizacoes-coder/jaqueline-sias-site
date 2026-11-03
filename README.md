# Jaqueline Sias Despachante — site institucional

Site institucional da **Jaqueline Sias Despachante**: Flask + Jinja2 no backend; HTML5, CSS3 e JavaScript puro no frontend. Pronto para Docker e produção com HTTPS automático.

O layout segue o design aprovado no Claude Design (`../Jaqueline Sias Despachante.html`): degradê roxo `#4D0D63 → #3E0A4F`, detalhes dourados, Montserrat + Poppins e ícones Lucide.

## Sumário

- [Estrutura](#estrutura)
- [Rodar localmente (Python)](#rodar-localmente-python)
- [Rodar com Docker](#rodar-com-docker)
- [Colocar no ar](#colocar-no-ar)
- [Configuração (.env)](#configuração-env)
- [Formulário de contato](#formulário-de-contato)
- [Editar conteúdo](#editar-conteúdo)
- [SEO](#seo)
- [Segurança e LGPD](#segurança-e-lgpd)
- [Testes](#testes)
- [Pendências de confirmação](#pendências-de-confirmação)

## Estrutura

```
jaqueline-sias-site/
├── app/
│   ├── __init__.py        # fábrica da app, cabeçalhos de segurança, helpers Jinja
│   ├── config.py          # configurações por ambiente (lidas do .env)
│   ├── content.py         # serviços, FAQ, avaliações, diferenciais (fonte única)
│   ├── contact.py         # entrega do formulário (arquivo JSONL e/ou e-mail)
│   ├── forms.py           # formulário + validações no backend
│   ├── routes.py          # páginas, sitemap, robots, healthcheck, erros
│   ├── templates/
│   │   ├── base.html, index.html, servicos.html, sobre.html,
│   │   ├── contato.html, privacidade.html, conteudo.html
│   │   ├── partials/      # seções reutilizadas entre as páginas
│   │   ├── artigos/       # artigos futuros (_modelo.html)
│   │   └── errors/        # 404.html, 500.html
│   └── static/
│       ├── css/           # style.css, components.css, responsive.css
│       ├── js/            # main.js, animations.js, whatsapp.js
│       ├── fonts/         # Montserrat e Poppins (Google Fonts, auto-hospedadas)
│       └── images/        # branding/, team/, services/, icons/, favicon/
├── tests/                 # pytest
├── run.py                 # ponto de entrada
├── gunicorn.conf.py
├── Dockerfile, docker-compose.yml, docker-compose.prod.yml, Caddyfile
├── requirements.txt, requirements-dev.txt
└── .env.example
```

### Páginas

| Rota | Conteúdo |
|---|---|
| `/` | One-page completa: início, sobre, serviços, diferenciais, avaliações, como funciona, FAQ, conteúdo, Instagram, contato |
| `/servicos` | Serviços, como funciona, FAQ e contato |
| `/sobre` | Sobre, diferenciais, avaliações e Instagram |
| `/contato` | Contato e formulário (GET/POST) |
| `/privacidade` | Política de Privacidade (LGPD) |
| `/conteudo` | Temas e artigos ("Informação que facilita sua vida") |
| `/sitemap.xml`, `/robots.txt`, `/site.webmanifest`, `/healthz` | Infraestrutura e SEO |

## Rodar localmente (Python)

Requer Python 3.12+.

```bash
cd jaqueline-sias-site
python -m venv .venv
# Windows: .venv\Scripts\activate   |   Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env        # ajuste SECRET_KEY e SITE_URL=http://localhost:8000
# para recarregar automaticamente ao editar: APP_ENV=development no .env
python run.py
```

Acesse http://localhost:8000.

## Rodar com Docker

```bash
cp .env.example .env        # ajuste SECRET_KEY e SITE_URL
docker compose up --build
```

Acesse http://localhost:8000. O container:

- usa `python:3.12-slim` e Gunicorn;
- roda como usuário sem privilégios (`uid 10001`), com sistema de arquivos somente leitura e `cap_drop: ALL`;
- tem healthcheck em `/healthz`;
- guarda as mensagens do formulário no volume `contatos` (`/app/instance/contatos.jsonl`).

Para ler as mensagens recebidas:

```bash
docker compose exec web cat /app/instance/contatos.jsonl
```

## Colocar no ar

### Opção A — VPS com Docker (recomendada)

Qualquer VPS Linux com Docker (Hostinger, DigitalOcean, Contabo, AWS Lightsail etc.). O Caddy emite e renova o certificado HTTPS sozinho.

1. Aponte o DNS do domínio (registros `A` de `@` e `www`) para o IP do servidor.
2. No servidor:
   ```bash
   git clone <repositório> && cd jaqueline-sias-site
   cp .env.example .env
   # edite: SECRET_KEY, SITE_URL=https://seudominio.com.br, DOMAIN=seudominio.com.br,
   #        SESSION_COOKIE_SECURE=true, TRUST_PROXY=true
   docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
   ```
3. Libere as portas 80 e 443 no firewall.

O Caddy redireciona `www.` para o domínio principal e comprime as respostas (gzip/zstd).

Para atualizar o site depois de mudanças:

```bash
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### Opção B — Plataforma gerenciada (Render, Railway, Fly.io)

Crie um serviço a partir do `Dockerfile`, defina as variáveis do `.env.example` no painel (com `TRUST_PROXY=true` e `SESSION_COOKIE_SECURE=true`) e conecte o domínio. A plataforma cuida do HTTPS. O sistema de arquivos costuma ser efêmero nesses serviços, então configure o envio por e-mail (SMTP) para não perder mensagens do formulário.

### Depois de publicar

1. Cadastre o domínio no [Google Search Console](https://search.google.com/search-console), use `GOOGLE_SITE_VERIFICATION` para verificar e envie `https://seudominio.com.br/sitemap.xml`.
2. Coloque o link do site no Perfil da Empresa no Google e na bio do Instagram.
3. Teste o compartilhamento do link no WhatsApp (a imagem Open Graph é `static/images/branding/og-image.jpg`).

## Configuração (.env)

Todas as variáveis estão documentadas em [`.env.example`](.env.example). As principais:

| Variável | Uso |
|---|---|
| `SECRET_KEY` | Obrigatória. Gere com `python -c "import secrets; print(secrets.token_hex(32))"` |
| `SITE_URL` | URL pública; usada em canonical, sitemap e Open Graph |
| `WHATSAPP_NUMBER` | DDI + DDD + número, só dígitos. **Vazio = nenhum link de WhatsApp é gerado** (os botões levam ao formulário) |
| `CONTACT_EMAIL`, `INSTAGRAM_URL` | Exibidos no contato e no rodapé |
| `BUSINESS_CITY`, `BUSINESS_STATE` | SEO local (título, Schema.org). Vazios = não exibidos |
| `BUSINESS_ADDRESS`, `MAPS_EMBED_URL` | Endereço e mapa: só preencha se forem públicos |
| `MAIL_*` | Envio das mensagens do formulário por e-mail |

Campos vazios não aparecem no site. Nada é inventado: se um dado não estiver configurado, a seção correspondente se adapta.

## Formulário de contato

- Campos: nome, telefone/WhatsApp, serviço (opcional), mensagem e consentimento (LGPD).
- Validação no navegador (JS) **e** no backend (WTForms). Funciona também sem JavaScript.
- Proteção CSRF, honeypot anti-spam e limite de 5 envios/minuto e 20/dia por IP.
- Entrega:
  - **Arquivo** `instance/contatos.jsonl` (padrão, `CONTACT_STORE_ENABLED=true`);
  - **E-mail** via SMTP, quando `MAIL_SERVER` estiver preenchido. Para Hotmail/Outlook: `smtp-mail.outlook.com`, porta `587`, TLS. Se a conta tiver verificação em duas etapas, use uma senha de aplicativo.
- Após o envio, o cliente vê um botão "Agilizar pelo WhatsApp" com mensagem já preenchida.

## Editar conteúdo

Textos de serviços, diferenciais, passos, FAQ, temas e avaliações ficam em [`app/content.py`](app/content.py). Altere ali e reinicie a aplicação.

**Publicar artigos** na seção Conteúdo:

1. Copie `app/templates/artigos/_modelo.html` para `app/templates/artigos/<slug>.html` e escreva o texto.
2. Adicione o artigo à lista `ARTICLES` em `app/content.py`:
   ```python
   {"slug": "<slug>", "title": "...", "description": "...", "topic": "Documentação veicular", "date": "2026-11-10"}
   ```
3. O artigo aparece em `/conteudo`, na home e no `sitemap.xml`.

**Imagens**: as fotos estão em WebP otimizado (`static/images/team` e `static/images/branding`). Para trocar uma foto, mantenha o mesmo nome e proporção, ou ajuste o template correspondente.

## SEO

- `title` e `meta description` exclusivos por página; um único `H1` por página.
- URLs amigáveis, `canonical`, Open Graph e Twitter Card.
- `sitemap.xml` e `robots.txt` dinâmicos (usam `SITE_URL`).
- Schema.org (JSON-LD): `WebSite`, `ProfessionalService` (somente com dados configurados), `FAQPage` e `BreadcrumbList`. Nenhuma nota ou avaliação agregada é declarada.
- Favicon, ícones PWA e `site.webmanifest`.
- Imagens com `alt`, dimensões declaradas, `srcset` e carregamento lento abaixo da dobra.

## Segurança e LGPD

- Credenciais apenas em variáveis de ambiente; `.env` fora do Git e da imagem Docker.
- CSP estrita (`script-src 'self'`, sem scripts ou estilos inline), `X-Frame-Options`, `nosniff`, `Referrer-Policy`, `Permissions-Policy` e HSTS quando em HTTPS.
- Cookies de sessão `HttpOnly`, `SameSite=Lax` e `Secure` em produção.
- Limite de tamanho de requisição (64 KB) e rate limiting (Flask-Limiter). Para mais de uma instância, use Redis em `RATELIMIT_STORAGE_URI`.
- Sem rastreadores de terceiros, sem Google Fonts remoto (fontes servidas pelo próprio site) e sem cookies além do de sessão. Por isso não há banner de cookies. Se no futuro for instalado Google Analytics/Meta Pixel, será preciso adicionar consentimento.
- O log de acesso não registra query strings; o arquivo de contatos não guarda IP.
- Política de Privacidade em `/privacidade`.

## Testes

```bash
pip install -r requirements-dev.txt
pytest -q
```

Cobrem: todas as rotas, SEO básico (H1 único, títulos e descrições exclusivos, canonical, alt, JSON-LD, sitemap, robots), links de WhatsApp e Instagram, comportamento sem número de WhatsApp, cabeçalhos de segurança, ausência de inline scripts/styles, CSRF, rate limit e todas as validações do formulário.

## Pendências de confirmação

Itens que dependem da Jaqueline antes do lançamento:

- [ ] Lista definitiva de serviços (os 7 do design foram mantidos; "serviços relacionados a multas" não foi incluído por não estar confirmado).
- [ ] Domínio do site.
- [ ] Endereço comercial / atendimento presencial e horário (hoje só aparece "Niterói, RJ").
- [ ] Link do Perfil da Empresa no Google (`GOOGLE_REVIEWS_URL`) para o botão "Ver no Google".
- [ ] Revisão das respostas do FAQ.
- [ ] Credenciais SMTP, se quiser receber o formulário por e-mail.
