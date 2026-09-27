# MarIA

Assistente virtual humanizado para o atendimento inicial de
profissionais autônomos de saúde mental (psicólogas, psicanalistas).

O MarIA responde às primeiras mensagens de quem procura a profissional:
tira dúvidas sobre a abordagem e o funcionamento do atendimento, ajuda
no pré-agendamento e — o ponto mais importante — reconhece sinais de
risco à vida e encaminha imediatamente aos serviços de emergência.

> **Delimitação fundamental:** o sistema é suporte administrativo e
> triagem. Ele **nunca** diagnostica, nunca dá aconselhamento clínico e
> nunca substitui a profissional. O canal não é plantão psicológico nem
> serviço de emergência, e deixa isso explícito para quem escreve.

Trabalho de Conclusão de Curso — Engenharia da Computação, Ibmec Barra
da Tijuca. Autor: Pedro Henrique Rossetto Costa. Orientador: Thiago
Souza.

---

## Como funciona, em uma imagem

```
  Paciente / lead                         Profissional
        │                                       │
   WhatsApp ou                              Painel web
  chat simulado                                 │
        │                                       │
        ▼                                       ▼
┌──────────────────────────────────────────────────────────┐
│                      API (FastAPI)                       │
│                                                          │
│   1. Triagem de segurança  ← roda antes de tudo          │
│        ├─ risco à vida → texto fixo + alerta             │
│        └─ sem risco ↓                                    │
│   2. RAG: busca nos documentos da profissional           │
│   3. Resposta gerada pela Claude, no tom dela            │
└──────────────────────────────────────────────────────────┘
        │                    │                   │
   PostgreSQL           ChromaDB          Google Calendar
  (conversas,          (documentos        (pré-agendamento)
   alertas)             vetorizados)
```

## Documentação

**Técnica** — para quem vai mexer no código:

| Documento | O que tem dentro |
|---|---|
| [Arquitetura](Documentation/tecnico/arquitetura.md) | Como as peças se encaixam, o caminho de uma mensagem, por que o canal é desacoplado |
| [Modelo de dados](Documentation/tecnico/modelo-de-dados.md) | Cada tabela, cada campo e a razão de existir |
| [Desenvolvimento](Documentation/tecnico/desenvolvimento.md) | Instalar, rodar, testar e mexer no banco com migrações |
| [Configuração](Documentation/tecnico/configuracao.md) | Variáveis de ambiente e as integrações externas (Google, Meta) |
| [Segurança e LGPD](Documentation/tecnico/seguranca-lgpd.md) | Criptografia, retenção, aviso de IA e o protocolo de risco |

**Funcionalidades** — o que cada uma faz, por que existe e como usar:
[índice](Documentation/funcionalidades/README.md) (triagem de segurança,
perfil e regras da MarIA, handoff e "Em consulta", alerta por e-mail).

**Do projeto** — para entender as decisões e o percurso do TCC:

| Documento | O que tem dentro |
|---|---|
| [Planejamento do projeto](Documentation/planejamento-projeto.md) | Contexto, princípios éticos, arquitetura combinada, roadmap |
| [Requisitos e MVP](Documentation/levantamento-requisitos-mvp.md) | Features priorizadas, requisitos funcionais, critérios de triagem |
| [Plano do MVP](Documentation/planejamento-mvp-9out.md) | Cronograma semanal, escopo congelado, riscos |
| [Telas web e mobile](Documentation/descricao-app-web-mobile.md) | Descrição das interfaces |

## Começando rápido

Pré-requisitos: [Docker Desktop](https://www.docker.com/products/docker-desktop/),
Python 3.12 e Node.js 18+.

```bash
# 1. Banco de dados
docker compose up -d

# 2. Backend (a partir da raiz do repositório)
cd backend
copy .env.example .env        # depois preencha as chaves
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head          # cria as tabelas
uvicorn app.main:app --reload

# 3. Front-end (em outro terminal, a partir da raiz)
cd frontend
copy .env.example .env
npm install
npm run dev
```

Depois da primeira instalação, no Windows, basta dar dois cliques em
`iniciar.bat` com o Docker Desktop aberto: ele sobe o banco, a API e o
painel e abre o navegador.

Painel em `http://localhost:5173`, API em `http://127.0.0.1:8000`, e a
documentação interativa da API em `http://127.0.0.1:8000/docs`.

O passo a passo completo, com o que preencher no `.env` e como resolver
os erros mais comuns, está em
[Desenvolvimento](Documentation/tecnico/desenvolvimento.md) e
[Configuração](Documentation/tecnico/configuracao.md).

## Estado atual

Funcionando:

- **Multi-tenant**: cada profissional tem base de conhecimento, tom de
  voz e conversas isoladas.
- **RAG**: documentos (`.pdf`, `.docx`, `.txt`, `.md`) são divididos,
  indexados no ChromaDB e consultados a cada mensagem.
- **Resposta via Claude**, no tom de voz configurado pela profissional.
- **Triagem de segurança** em duas camadas (regras fixas e modelo), com
  quatro níveis, texto fixo de emergência e falha fechada.
- **Perfil e regras da MarIA**: tom de voz, exemplos, valores na
  primeira resposta e a lista fixa do que ela nunca diz.
- **Handoff**: a profissional assume, responde e devolve ao bot; pedido
  de humano, recusa do bot e botão "Em consulta".
- **Alerta por e-mail** para a profissional, sem conteúdo da conversa
  (falta configurar a conta de envio).
- **Login com Google**, só para e-mails convidados, com todas as rotas
  de gestão protegidas e cada profissional vendo só os próprios dados
  (falta o Client ID do Google).
- **Cadastro em 7 etapas** no primeiro acesso, no visual do protótipo,
  com aceite das regras da MarIA (falta conectar o WhatsApp, em 05/10).
- **Painel** no visual do protótipo: menu, "Em consulta" no topo,
  Perfil do atendimento, Base de conhecimento (enviar e remover
  documentos) e o simulador "Testar a MarIA", com o que a triagem
  decidiu em cada resposta.
- **LGPD básico**: conteúdo das mensagens e dados de contato cifrados em
  repouso, aviso automático de que é uma IA, política de retenção.
- **Integrações preparadas**: Google Calendar (conta de serviço,
  conexão validada) e WhatsApp Cloud API (número verificado, token
  permanente).

Em construção, na ordem do
[plano do MVP](Documentation/planejamento-mvp-9out.md):

- Triagem de mensagens quebradas em várias partes
- Webhook do WhatsApp e envio de mensagens
- Painel: Conversas e Alertas (com as telas de celular), WhatsApp e Agenda
- Pré-agendamento no Google Calendar

## Estrutura do repositório

```
.
├── backend/              API em FastAPI + PostgreSQL + ChromaDB
│   ├── alembic/            migrações do banco
│   ├── app/                código da aplicação
│   ├── scripts/            tarefas manuais (ex.: retenção de dados)
│   └── tests/              testes automatizados (pytest)
├── frontend/             painel da profissional (React + Vite)
├── Documentation/        documentação do projeto e técnica
└── docker-compose.yml    sobe o PostgreSQL local
```
