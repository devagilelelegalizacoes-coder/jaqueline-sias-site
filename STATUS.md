# Status do projeto — onde paramos

**Última atualização:** 03/11/2026

## Concluído

- [x] Design do Claude Design (`Jaqueline Sias Despachante.html`) convertido em Flask + Jinja2, HTML/CSS/JS puro.
- [x] Seções: Home, Sobre, Serviços (7), Diferenciais (bento), Avaliações do Google (20), Como funciona, FAQ, Conteúdo, Instagram, Contato.
- [x] Páginas: `/`, `/servicos`, `/sobre`, `/contato`, `/privacidade`, `/conteudo` + 404/500.
- [x] Formulário com validação (navegador e backend), CSRF, honeypot e limite de envios; mensagens salvas em `instance/contatos.jsonl` (SMTP opcional).
- [x] WhatsApp flutuante e links por serviço (`WHATSAPP_NUMBER` no `.env`).
- [x] SEO: títulos únicos, canonical, Open Graph, sitemap, robots, Schema.org (ProfessionalService, FAQPage, Breadcrumb).
- [x] Segurança: CSP estrita, cabeçalhos, cookies seguros, usuário não-root no Docker.
- [x] Docker (`docker compose up --build`) e produção com HTTPS via Caddy (`docker-compose.prod.yml`).
- [x] 34 testes automáticos passando (`pytest -q`).
- [x] Testado em 360, 390, 430, 768, 1366 e 1920 px, sem erros de console.
- [x] Lighthouse: Acessibilidade, Boas práticas e SEO 100; Performance 100 desktop / 91–99 mobile (local, sem compressão).
- [x] Código publicado no GitHub (repositório privado).

## Próximos passos

1. **Hospedagem e domínio** — definir onde o site vai rodar (VPS com Docker é a opção recomendada; ver README, "Colocar no ar").
2. Criar o `.env` de produção: `SECRET_KEY` nova, `SITE_URL`, `DOMAIN`, `SESSION_COOKIE_SECURE=true`, `TRUST_PROXY=true`.
3. Publicar e cadastrar no Google Search Console (enviar `sitemap.xml`).

## Pendências de confirmação com a Jaqueline

- [ ] Lista definitiva de serviços ("serviços relacionados a multas" ficou de fora).
- [ ] Confirmar que as 20 avaliações do Google podem ser exibidas no site.
- [ ] Endereço comercial e horário de atendimento (se forem públicos).
- [ ] Link do Perfil da Empresa no Google (`GOOGLE_REVIEWS_URL`).
- [ ] Revisão das respostas do FAQ.
- [ ] Credenciais SMTP, se quiser receber o formulário por e-mail.

## Como retomar

```bash
git clone https://github.com/devagilelelegalizacoes-coder/jaqueline-sias-site.git
cd jaqueline-sias-site
cp .env.example .env      # gerar SECRET_KEY e ajustar SITE_URL
docker compose up --build # http://localhost:8000
```
