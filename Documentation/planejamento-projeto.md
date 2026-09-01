# Chat Humanizado TCC — Planejamento e Decisões do Projeto

> Documento de referência com as decisões já combinadas para o desenvolvimento do protótipo. Atualizado conforme o projeto avança.

## 1. Contexto do projeto

- **Título**: Chatbot Humanizado para Atendimento em Saúde Mental — Uma Proposta de Assistente Virtual Customizável
- **Autor**: Pedro Henrique Rossetto Costa
- **Orientador**: Thiago Souza
- **Instituição**: Centro Universitário Ibmec Barra da Tijuca
- **Objetivo geral**: desenvolver um protótipo de assistente virtual humanizado, baseado em IA Generativa, para automatizar o atendimento inicial, a triagem de segurança e o suporte administrativo de profissionais independentes de saúde mental.
- **Delimitação central**: o sistema atua estritamente como suporte administrativo e triagem — **nunca realiza diagnóstico ou intervenção clínica**.
- **Visão de produto (foco principal a partir de agora)**: não é um bot único para um profissional — é uma **plataforma multi-tenant**, onde cada profissional poderá se cadastrar, treinar seu próprio RAG e conectar seu próprio WhatsApp. A arquitetura é desenhada com isso em mente desde já; login completo, cobrança/assinatura e onboarding self-service do WhatsApp **não precisam estar prontos para a defesa** — entram como *trabalhos futuros* no TCC.
- **Nota (01/09/2026)**: chegou a ser implementado login do profissional via Google (OAuth 2.0) adiantando esse trabalho futuro, mas essa decisão foi revertida — o login foi considerado precoce nesta fase. O projeto voltou a seguir a ordem original do roadmap (seção 8), com identificação apenas por `slug`, sem autenticação.

### Os três módulos do sistema

1. **Customização** — engenharia de prompt + RAG, permitindo que o profissional configure o tom de voz e a base de conhecimento via upload de documentos.
2. **Administrativo** — pré-agendamento via integração com o Google Calendar e validação de comprovante de pagamento via PIX (visão computacional).
3. **Triagem de segurança** — detecção de padrões de risco e encaminhamento automático a recursos de emergência (CVV 188).

---

## 2. Princípios éticos e de segurança combinados

- O sistema **nunca** tenta diagnosticar ou dar aconselhamento clínico.
- O módulo de triagem de segurança é desenhado em nível de **arquitetura e lógica de decisão**; os mecanismos detalhados de detecção não são construídos de forma que possam ser estudados para burlar o sistema.
- Em caso de dúvida, a triagem deve **favorecer falsos positivos sobre falsos negativos** — melhor alertar um caso que não precisava do que deixar passar um que precisava.
- O **protocolo de segurança é uma decisão clínica**, não técnica: precisa ser desenhado em conjunto com a profissional (o que ela considera sinal de risco, quão conservador o sistema deve ser, como ela quer ser notificada).
- Dados de pacientes são dados sensíveis (LGPD). Antes de qualquer dado real entrar no sistema, é necessário: criptografia dos dados sensíveis, aviso claro ao paciente de que está falando com um assistente de IA (transparência), e uma política simples de retenção de dados.
- Antes de um lançamento com pacientes reais: a profissional precisa testar extensivamente o sistema (incluindo cenários difíceis) e revisar transcritos antes de confiar nele.
- O lançamento com pacientes reais deve ser **gradual e supervisionado** — a profissional acompanhando de perto as primeiras conversas, com capacidade de intervir a qualquer momento.

---

## 3. Arquitetura do sistema (fluxo da mensagem)

```
Paciente
   ↓
Canal de mensagens (WhatsApp ou chat simulado)
   ↓
Núcleo orquestrador (roteamento da conversa)
   ↓
Triagem de segurança (verificação prioritária — roda ANTES de tudo)
   ├── Risco identificado → contato CVV 188 + alerta imediato ao profissional
   └── Sem risco          → RAG + geração de resposta (LLM) → módulo administrativo (se aplicável)
   ↓
Resposta enviada ao paciente
```

**Decisões-chave dessa arquitetura:**
- A **triagem de segurança roda primeiro**, como um gate prioritário — se detectar risco, o sistema segue um caminho fixo e previsível (CVV + alerta), sem tentar ser "inteligente" nesse momento.
- A **camada de canal é desacoplada** do núcleo do sistema — o desenvolvimento pode seguir com um canal simulado (chat web simples) enquanto o WhatsApp real é configurado em paralelo, sem precisar reescrever o núcleo depois.
- O **RAG** garante que informações sobre valores, horários e abordagem terapêutica venham dos documentos reais do profissional, não de invenção do modelo.
- **Multi-tenancy desde o início**: nenhum endpoint tem `professional_id` fixo no código. O identificador do profissional (por enquanto, algo simples como um slug — sem exigir login completo ainda) é sempre um parâmetro, tanto no upload de documentos quanto no chat e no painel de gerenciamento. Cada profissional tem sua própria coleção no ChromaDB, isolada das demais. Isso permite demonstrar dois ou mais profissionais funcionando lado a lado, com tom de voz e base de conhecimento diferentes, provando o conceito de plataforma sem precisar de autenticação completa, cobrança ou onboarding self-service do WhatsApp ainda.
- O roteamento de mensagens do WhatsApp para o profissional correto usa o `phone_number_id` que já vem no payload do webhook da Meta — cada número de WhatsApp registrado mapeia para um profissional no banco.

---

## 4. Stack tecnológica

| Componente | Escolha | Motivo |
|---|---|---|
| Backend | Python + FastAPI | Ecossistema forte para RAG, visão computacional e webhooks; comum em bancas de Engenharia da Computação |
| ORM | SQLAlchemy | Abstrai o banco de dados — permite trocar de banco sem reescrever queries |
| Banco de dados | PostgreSQL, local via Docker (dev) → hospedado (produção) | Evita duas camadas de risco: nem a fricção de banco hospedado durante o desenvolvimento, nem surpresas de dialeto SQL ao migrar depois — já é Postgres desde o início |
| Vetores (RAG) | ChromaDB | Leve, roda local, suficiente para um protótipo acadêmico |
| LLM | Claude API (Sonnet 5, com Haiku 4.5 como alternativa mais barata) | Precisa de API key própria da Anthropic (separada da conta do WhatsApp) |
| Canal | WhatsApp Business API (Meta Cloud API, direto, sem BSP) | Sem taxa de plataforma intermediária; mensagens de resposta dentro de 24h são gratuitas |
| Agendamento | Google Calendar API | Sincroniza com a agenda real do profissional, evitando conflitos de horário |

---

## 5. Status da integração com WhatsApp

- Conta de desenvolvedor Meta criada; app **"Chat Humanizado TCC"** configurado com o caso de uso "Conectar-se com os clientes pelo WhatsApp".
- Número de teste (EUA) funcional e validado.
- **Descoberta importante**: desde set/2025, a Meta restringe mensagens entre países envolvendo o Brasil — o número de teste americano não consegue mandar mensagem para números brasileiros. *(Isso é material relevante para a seção de limitações do TCC.)*
- **Solução em andamento**: cadastrar um número de telefone brasileiro real na Etapa 2 (Configuração de produção), usando um eSIM pré-pago digital ou um celular emprestado só para a verificação por SMS/ligação.

---

## 6. Estimativa de custos (referência, a validar com uso real)

- **Claude API**: ~US$10–40/mês para algumas centenas de conversas/mês (Sonnet 5); metade disso com Haiku 4.5. Modelo pay-as-you-go, sem mensalidade fixa.
- **WhatsApp**: mensagens de resposta dentro de 24h a um contato iniciado pelo paciente são **gratuitas**. Só mensagens proativas fora dessa janela (ex.: lembretes) têm custo pequeno (centavos por mensagem).
- **Hospedagem (VPS)**: ~R$25–60/mês para um servidor sempre ligado, já incluindo o Postgres rodando no mesmo servidor.
- **Total estimado inicial**: ~R$100–250/mês, a maior parte sendo a API do LLM.

---

## 7. Estrutura do código já criada

```
Chatbot-Humanizado-para-profissionais-de-saude-mental/
├── docker-compose.yml       # sobe o Postgres local
├── backend/                  # API em FastAPI
│   ├── requirements.txt
│   ├── .env.example
│   ├── pytest.ini
│   ├── tests/                  # testes automatizados (pytest)
│   └── app/
│       ├── main.py                # ponto de entrada do FastAPI, CORS
│       ├── config.py               # variáveis de ambiente
│       ├── database.py              # conexão SQLAlchemy
│       ├── models.py                 # tabelas: Professional, Document, Conversation, Message
│       ├── schemas.py                 # formatos de entrada/saída da API
│       ├── routers/
│       │   ├── professionals.py         # cadastro/edição de profissionais (por slug)
│       │   ├── documents.py             # upload e indexação de documentos (por slug)
│       │   └── chat.py                    # canal simulado (POST /chat/simulate, público) — RAG + Claude
│       └── services/
│           ├── text_extraction.py           # extração e chunking de documentos
│           ├── rag.py                        # ChromaDB, uma coleção por profissional
│           └── llm.py                         # prompt de sistema + chamada à API da Claude
└── frontend/                  # painel simples (React + Vite)
    └── src/
        ├── App.jsx               # renderiza o painel
        ├── api.js                  # chamadas à API por slug
        └── pages/
            └── Dashboard.jsx          # carregar por slug, editar tom de voz, documentos
```

*(SafetyAlert ainda não foi criado — entra junto da triagem de segurança, item 3 do roadmap.)*

---

## 8. Roadmap — próximos passos

1. ~~**Finalizar RAG + resposta real, já multi-tenant**~~ — ✅ concluído. Upload de documentos e chat recebem o profissional como parâmetro (slug); coleção própria no ChromaDB por profissional; resposta real via Claude API no lugar do placeholder. Inclui também um painel simples (front-end) pra gerenciar tom de voz e documentos por slug.
2. **Desenhar o protocolo de segurança com a profissional** (aguardando) — o que ela considera sinal de risco, quão conservador o sistema deve ser, como ela quer ser notificada. Roteiro de entrevista pronto em `Entrevista_Marilia_Protocolo_Seguranca.md`, aguardando a conversa.
3. **Construir a triagem de forma conservadora** — priorizando alertar demais a deixar passar um caso real. Depende do passo 2.
4. ~~**Resolver o básico de LGPD**~~ — ✅ concluído (adiantado enquanto o passo 2 aguarda resposta da profissional). Criptografia do conteúdo das mensagens em repouso (transparente via um `TypeDecorator` do SQLAlchemy), aviso automático e determinístico de que é um assistente de IA logo na primeira mensagem de cada conversa (não depende do modelo lembrar de avisar), e uma política de retenção definida (90 dias, configurável via `DATA_RETENTION_DAYS`) com um script manual (`backend/scripts/purge_old_conversations.py`) para aplicá-la — sem automação agendada ainda, já que não há dados reais em produção nesta fase.
5. **A profissional testa extensivamente** — antes de qualquer paciente real interagir com o sistema.
6. **Lançamento gradual e supervisionado** — acompanhamento próximo nas primeiras semanas, com capacidade de intervenção imediata.

### Trabalhos futuros (fora do escopo da defesa)

- Login e cadastro completo dos profissionais
- Cobrança/assinatura (ex.: integração com Stripe)
- Onboarding self-service do WhatsApp — Meta oferece um caminho para isso via o programa **"Provedor de Tecnologia"** (Embedded Signup), permitindo que cada profissional conecte seu próprio número sem passar pelo console de desenvolvedor manualmente
- Validação de comprovante de pagamento via PIX por visão computacional (parte do módulo Administrativo, ainda não priorizada)

---

## 9. Fluxo de trabalho do projeto

- Implementação prática do código: **Claude Code** (dentro do VSCode).
- Planejamento, decisões de arquitetura, dúvidas conceituais e revisão de trade-offs: **este chat**.
