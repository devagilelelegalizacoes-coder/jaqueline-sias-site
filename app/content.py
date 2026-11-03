"""Conteúdo institucional do site.

Fonte única para serviços, diferenciais, FAQ, avaliações e temas de conteúdo.
Edite aqui para atualizar o site. Publique somente informações confirmadas
pela Jaqueline: não inclua prazos, valores ou garantias sem validação.
"""

SERVICES = [
    {
        "slug": "transferencia-de-propriedade",
        "name": "Transferência de propriedade",
        "icon": "arrow-left-right",
        "desc": "Orientação e condução da transferência do veículo para o novo proprietário.",
    },
    {
        "slug": "primeiro-emplacamento",
        "name": "Primeiro emplacamento",
        "icon": "car-front",
        "desc": "Registro e emplacamento de veículo zero quilômetro.",
    },
    {
        "slug": "licenciamento-veicular",
        "name": "Licenciamento veicular",
        "icon": "calendar-check",
        "desc": "Apoio no licenciamento anual para manter o veículo apto a circular.",
    },
    {
        "slug": "regularizacao-documental",
        "name": "Regularização documental",
        "icon": "file-check",
        "desc": "Análise e regularização de pendências na documentação do veículo.",
    },
    {
        "slug": "consulta-de-debitos-e-restricoes",
        "name": "Consulta de débitos e restrições",
        "icon": "search",
        "desc": "Levantamento de débitos, multas e restrições antes de comprar, vender ou regularizar.",
    },
    {
        "slug": "segunda-via-de-documentos",
        "name": "Segunda via de documentos",
        "icon": "copy",
        "desc": "Solicitação de nova via de documentos do veículo em caso de perda, roubo ou dano.",
    },
    {
        "slug": "alteracao-cadastral-e-caracteristicas",
        "name": "Alteração cadastral e características",
        "icon": "settings-2",
        "desc": "Atualização de dados do proprietário e alteração de características do veículo.",
    },
]

DIFFERENTIALS = [
    {
        "icon": "user-round-check",
        "title": "Atendimento personalizado",
        "desc": "Cada veículo e cada cliente têm uma situação própria. O atendimento parte do seu caso, sem respostas padronizadas.",
        "variant": "feature",
    },
    {
        "icon": "message-circle",
        "title": "Comunicação transparente",
        "desc": "Informações claras sobre documentos, etapas e o que depende de cada parte.",
        "variant": "dark",
    },
    {
        "icon": "compass",
        "title": "Orientação durante o processo",
        "desc": "Você sabe o que está acontecendo e o que precisa fazer em cada momento.",
        "variant": "light",
    },
    {
        "icon": "smartphone",
        "title": "Praticidade no atendimento",
        "desc": "Contato direto pelo WhatsApp para tirar dúvidas e enviar informações.",
        "variant": "light",
    },
    {
        "icon": "list-checks",
        "title": "Acompanhamento das solicitações",
        "desc": "Seu processo é acompanhado de perto até a conclusão.",
        "variant": "wide",
    },
]

STEPS = [
    {
        "title": "Entre em contato.",
        "desc": "Envie uma mensagem pelo WhatsApp ou pelo formulário do site.",
    },
    {
        "title": "Informe o serviço desejado e os dados necessários.",
        "desc": "Conte qual é a sua necessidade e os dados do veículo.",
    },
    {
        "title": "Receba orientação sobre os próximos passos.",
        "desc": "Você recebe a lista de documentos e as etapas do seu processo.",
    },
]

FAQS = [
    {
        "q": "Quais documentos são necessários para transferir um veículo?",
        "a": "A relação varia conforme o caso, mas costuma incluir documento de identificação e comprovante de residência do comprador, o documento de transferência (ATPV-e ou CRV) preenchido e assinado, e a vistoria do veículo. Antes de iniciar, eu confirmo com você a lista exata para a sua situação.",
    },
    {
        "q": "Como consultar débitos de um veículo?",
        "a": "Débitos como IPVA, licenciamento e multas podem ser consultados pela placa e pelo RENAVAM nos canais oficiais do DETRAN-RJ e da Secretaria de Fazenda. Se preferir, faço o levantamento completo para você, incluindo eventuais restrições.",
    },
    {
        "q": "Como funciona o primeiro emplacamento?",
        "a": "É o registro inicial de um veículo zero quilômetro. Envolve a nota fiscal, os documentos do proprietário e as etapas exigidas pelo DETRAN-RJ até a emissão do documento e a instalação das placas. Eu oriento cada etapa.",
    },
    {
        "q": "Como regularizar a documentação do veículo?",
        "a": "O primeiro passo é identificar a pendência: débitos, licenciamento atrasado, restrições ou divergências cadastrais. A partir do diagnóstico, explico o que precisa ser feito e conduzo o processo.",
    },
    {
        "q": "É possível solicitar atendimento pelo WhatsApp?",
        "a": "Sim. O WhatsApp é o canal mais rápido para falar comigo, tirar dúvidas e enviar as informações iniciais do seu caso.",
    },
    {
        "q": "Como saber quais serviços estão disponíveis?",
        "a": "Os serviços estão listados nesta página. Se a sua necessidade não aparecer na lista, mande uma mensagem e eu informo se posso ajudar.",
    },
]

TOPICS = [
    {
        "icon": "file-text",
        "title": "Documentação veicular",
        "desc": "Quais documentos o veículo precisa ter e quando cada um é exigido.",
    },
    {
        "icon": "scale",
        "title": "Legislação de trânsito",
        "desc": "Mudanças nas regras e o que elas significam para o proprietário.",
    },
    {
        "icon": "shield-check",
        "title": "Cuidados com o veículo",
        "desc": "Hábitos que evitam pendências e surpresas na hora de vender.",
    },
    {
        "icon": "clipboard-list",
        "title": "Processos administrativos",
        "desc": "Como funcionam as etapas de cada processo junto aos órgãos de trânsito.",
    },
]

# Artigos publicados. Para publicar, adicione um item e crie o template
# app/templates/artigos/<slug>.html (veja README, seção "Publicar artigos").
ARTICLES: list[dict] = [
    # {"slug": "como-transferir-veiculo-rj", "title": "...", "description": "...",
    #  "topic": "Documentação veicular", "date": "2026-11-10"},
]

# Avaliações públicas de clientes no perfil da Jaqueline Sias Despachante no Google,
# reproduzidas como publicadas (textos longos foram abreviados com "…").
REVIEWS = [
    ("Rayssa Bonfim", "Gostaria de expressar minha gratidão e reconhecimento pelo excelente trabalho realizado na regularização do meu veículo. Todo o processo foi conduzido com muita transparência, atenção, profissionalismo e clareza nas explicações, o que…"),
    ("Jean Pilla", "Atendimento diferenciado, a Jaqueline é uma excelente profissional, fiz contato aqui do RS e ela resolveu eu 3 dias o meu problema com serenidade, competência, pessoa de extrema confiança. Super indico o trabalho dela."),
    ("Anderson Urquiza", "Excelente atendimento e profissionalismo! Já utilizo os serviços há alguns anos e sempre fui muito bem atendido. Trabalho ágil, transparente e de total confiança. Recomendo com toda certeza. Parabéns pelo excelente trabalho, Jaque!"),
    ("Vitor Saito", "Jaqueline foi extremamente atenciosa e prestativa do início do contato a finalização do serviço. Todo o processo de transferência de propriedade foi guiado de forma clara, oferecendo todo o suporte necessário. Recomendo os serviços!"),
    ("Mercado facil", "Muito bom o serviço que me foi prestado. A Jaqueline me deu todo suporte e apoio, muito paciente e gentil, e o meu caso era bem complicado. Mas conseguirmos resolver graças a Deus!!"),
    ("Adão do Nascimento Pereira", "Excelente Profissional, recomendo! Atenciosa , profissional, ética e com foco total na solução do problema. Muito satisfeito com a experiência e relação comercial que tivemos ."),
    ("João Paulo Corrêa da Costa", "Jaqueline é uma excelente profissional! Em todo o processo sempre foi muito atenciosa e ágil. Com certeza sempre que precisar já sei a quem recorrerei!😄"),
    ("Regina Lazzaro", "Nota 1000 profissional.competente, atenciosa ,prática e rápida. Quem dera que no Brasil.tivessemos mais Jaqueline"),
    ("Jaqueline Braga", "Sabe quando você encontra uma profissional que faz TUDO com dedicação, carinho e competência? Pois é! Preciso elogiar publicamente a Jaqueline Sias Despachante, pelo trabalho impecável na documentação da minha moto. Resolveu tudo com…"),
    ("Lucas Moura", "Gostaria de minha gratidão e pelo excelente atendimento prestado pela Jaqueline Sias. Além de demonstrar grande conhecimento técnico, ela foi extremamente atenciosa e…"),
    ("Cintia Castro", "Minha experiência foi excelente, tudo dentro do prazo conforme prometido. Recomendo o serviço."),
    ("Luiz Henrique Penetra", "Fiquei muito satisfeito com o atendimento da dispachante Jaqueline. Muito atenciosa e eficiente. Resolveu com muita rapidez minha solicitação. Recomendo."),
    ("Juliane Neves", "Profissional excelente, competente, atenciosa, ágil, sempre atende com dedicação. Recomendo de olhos fechados !"),
    ("Stephany Mota", "Excepcional, muito atenciosa!! Com certeza tudo que eu precisar no detran , já sei a quem recorrer!"),
    ("Rodolfo Oliveira", "Super indico, profissional excelente e muito ágil, resolveu muito rápido o meu caso ."),
    ("Andre Freitas", "Excelente! Fez tudo rápido e não tive trabalho nenhum. Recomendo muito!"),
    ("Eduardo Ferreira", "Uma profissional muito competente, com a solução imediata para minhas demandas. Super indico ."),
    ("Marcelo Pereira Gonçalves", "excelente profissional, compromissada e agilidade no trabalho super recomendo"),
    ("Luciana Regina Lindo", "De confiança, atenciosa, resolveu tudo bem rápido. Recomendo."),
    ("Rafael Alvares", "Excelente profissional, suporte rápido/eficiente. Recomendo!"),
]
REVIEWS = [{"name": n, "text": t, "initial": n[0].upper()} for n, t in REVIEWS]

INSTAGRAM_GALLERY = [
    {"src": "images/team/jaqueline-institucional.webp", "alt": "Material institucional: Jaqueline Sias Despachante", "w": 800, "h": 800, "pos": "left"},
    {"src": "images/branding/logo-parede-vidro.webp", "alt": "Logotipo Jaqueline Sias Despachante aplicado em parede de vidro", "w": 800, "h": 600},
    {"src": "images/team/jaqueline-retrato.webp", "alt": "Material institucional: retrato de Jaqueline Sias", "w": 600, "h": 1067, "pos": "top"},
    {"src": "images/branding/logo-fundo-roxo.webp", "alt": "Logotipo Jaqueline Sias Despachante", "w": 800, "h": 453},
]

SERVICE_NAMES = [s["name"] for s in SERVICES]
