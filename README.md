# Chatbot Humanizado para Profissionais de Saúde Mental

TCC: assistente de IA multi-tenant para profissionais autônomos de saúde
mental (psicólogos, psicanalistas etc.), com atendimento humanizado,
recuperação de contexto via RAG e integração com a API da Claude.

Detalhes de arquitetura e decisões de produto estão em
`Documentation/planejamento-projeto.md`.

## Status atual (roadmap item 1)

Implementado até aqui:

- **Multi-tenant por slug**: cada profissional tem um `slug` único; todas
  as chamadas de upload/edição/chat informam explicitamente qual
  profissional estão usando (sem login/autenticação — decisão
  deliberada do roadmap, ver `planejamento-projeto.md`).
- **Upload de documentos**: `.pdf`, `.docx`, `.txt` e `.md` são
  extraídos, divididos em pedaços (chunks) e indexados numa coleção
  isolada do ChromaDB por profissional.
- **Chat com RAG real**: cada mensagem busca os trechos mais relevantes
  dos documentos daquele profissional e envia isso, junto com o
  histórico da conversa, para a API da Claude.
- **Painel simples (front-end)**: uma tela onde, informando o slug do
  profissional, dá pra editar o tom de voz, enviar/listar documentos e
  testar o chat diretamente — sem login, chamando os mesmos endpoints
  por slug.
- **LGPD básico**: o conteúdo das mensagens é criptografado em repouso
  no banco; toda nova conversa recebe automaticamente um aviso de que é
  um assistente de IA (não depende do modelo lembrar de avisar); e há
  uma política de retenção (90 dias, configurável) aplicável por um
  script manual.

Ainda não implementado (próximos itens do roadmap): protocolo de
segurança/triagem (aguardando conversa com a profissional), testes
extensivos, lançamento supervisionado.

## Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
  instalado e aberto (com virtualização habilitada na BIOS — em Windows,
  o Docker Desktop avisa se isso estiver faltando).
- Python 3.12 instalado.
- Node.js 18+ instalado (para o front-end).
- Uma chave de API da Anthropic (Claude) — veja em
  [console.anthropic.com](https://console.anthropic.com).

## Como rodar do zero (primeira vez numa máquina)

Rodado a partir da raiz do repositório, a não ser onde indicado.

1. **Suba o banco de dados (Postgres via Docker)**

   ```
   docker compose up -d
   ```

   Isso baixa e roda um container Postgres 16 em segundo plano, ouvindo
   em `localhost:5432`. Precisa do Docker Desktop aberto, mas não precisa
   deixar nenhum terminal aberto para o container continuar rodando.

2. **Backend — crie o arquivo de variáveis de ambiente**

   ```
   cd backend
   copy .env.example .env
   ```

   Abra o `backend\.env` e preencha `ANTHROPIC_API_KEY` com sua chave.
   Esse arquivo **não vai para o Git** (está no `.gitignore`) — cada
   máquina precisa do seu próprio. Deixe `DATA_ENCRYPTION_KEY` em branco
   por enquanto — o próximo passo instala o pacote necessário pra
   gerá-la.

3. **Backend — crie o ambiente virtual e instale as dependências**
   (ainda dentro de `backend/`)

   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

   O `.venv/` também não vai para o Git — é recriado em cada máquina.

   Com as dependências instaladas, volte ao `backend\.env` e preencha
   `DATA_ENCRYPTION_KEY`:
   ```
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

4. **Backend — rode a API** (ainda dentro de `backend/`)

   ```
   uvicorn app.main:app --reload
   ```

   Ao subir, a aplicação cria/atualiza as tabelas do Postgres
   automaticamente. Você deve ver `Application startup complete` no
   terminal.

5. **Frontend — instale e rode** (num segundo terminal, a partir da raiz)

   ```
   cd frontend
   copy .env.example .env
   npm install
   npm run dev
   ```

   Acesse `http://localhost:5173` no navegador.

## Como rodar no dia a dia (já configurado antes)

Em dois terminais, a partir da raiz do repositório:

```
docker compose up -d
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload
```

```
cd frontend
npm run dev
```

Para parar: `Ctrl+C` em cada terminal. O container do Postgres continua
rodando até você rodar `docker compose down` ou fechar o Docker Desktop
— não precisa parar ele toda vez.

## Testando

### Pelo front-end

1. Acesse `http://localhost:5173`.
2. Digite o slug de um profissional já cadastrado (crie um antes pelo
   `/docs`, veja abaixo) e clique em "Carregar".
3. Edite o tom de voz e/ou envie documentos (`.pdf`/`.docx`/`.txt`/`.md`)
   — a lista de documentos já enviados aparece logo abaixo.

### Pelo `/docs` (Swagger)

- **Health check**: `http://127.0.0.1:8000/health` → `{"status":"ok"}`.
- **`/docs`**: permite testar todos os endpoints pelo navegador.

#### Fluxo de teste sugerido

1. **Criar um profissional** — `POST /professionals`
   ```json
   {
     "slug": "marilia",
     "name": "Marília Rossetto",
     "voice_tone": "acolhedor e direto"
   }
   ```

2. **Enviar um documento sobre a prática dela** — `POST /documents/upload`
   (multipart/form-data)
   - `professional_slug`: `marilia`
   - `file`: um `.txt`/`.pdf`/`.docx` com informações reais (horários,
     forma de atendimento, valores, etc.)

3. **Conversar com o bot** — `POST /chat/simulate`
   ```json
   {
     "professional_slug": "marilia",
     "message": "Quais são os horários de atendimento?"
   }
   ```
   A resposta traz `reply` (texto gerado pela Claude usando o contexto
   recuperado), `sources` (quais documentos foram usados) e, só na
   primeira mensagem de cada conversa nova, `disclaimer` (o aviso fixo
   de que é um assistente de IA). Reenviando com o mesmo `session_id` da
   resposta anterior continua a mesma conversa, sem repetir o aviso.

### Testes automatizados

Requer o Postgres do `docker compose` rodando (alguns testes fazem
chamadas reais ao banco). De dentro de `backend/`, com o venv ativado:

```
pytest
```

### Retenção de dados (LGPD)

Conversas com mais de `DATA_RETENTION_DAYS` (padrão: 90) podem ser
removidas rodando manualmente, de dentro de `backend/`:

```
python scripts/purge_old_conversations.py
```

Não há agendamento automático ainda — é rodado quando necessário.

## Estrutura do projeto

```
Chatbot-Humanizado-para-profissionais-de-saude-mental/
├── docker-compose.yml       # sobe o Postgres usado pelo backend
├── Documentation/            # planejamento, entrevistas, decisões de produto
├── backend/                   # API em FastAPI
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── .env.example / .env      # .env é local, não vai pro Git
│   ├── tests/                    # testes automatizados (pytest)
│   ├── scripts/
│   │   └── purge_old_conversations.py  # aplica a política de retenção (LGPD)
│   └── app/
│       ├── main.py                 # cria a app FastAPI, CORS, registra as rotas
│       ├── config.py                # lê variáveis de ambiente (.env)
│       ├── database.py               # conexão com Postgres via SQLAlchemy
│       ├── models.py                  # tabelas: Professional, Document, Conversation, Message
│       ├── schemas.py                  # formatos de entrada/saída da API (Pydantic)
│       ├── routers/
│       │   ├── professionals.py          # cadastro e edição de profissionais (por slug)
│       │   ├── documents.py              # upload e listagem de documentos (por slug)
│       │   └── chat.py                     # chat com RAG + Claude (público) + aviso de IA
│       └── services/
│           ├── crypto.py                     # criptografia do conteúdo das mensagens (LGPD)
│           ├── text_extraction.py             # extrai texto de pdf/docx/txt e divide em chunks
│           ├── rag.py                          # ChromaDB: uma coleção por profissional
│           └── llm.py                           # monta o prompt e chama a API da Claude
└── frontend/                   # painel em React + Vite
    ├── package.json
    ├── .env.example / .env      # .env é local, não vai pro Git
    └── src/
        ├── App.jsx               # renderiza o painel
        ├── api.js                  # wrapper de chamadas à API (por slug)
        └── pages/
            └── Dashboard.jsx         # painel: carregar por slug, tom de voz, documentos
```

## Problemas comuns

- **`docker compose up -d` diz "no configuration file provided: not
  found"** — você não está na pasta do projeto. Rode `cd` até a pasta
  que contém o `docker-compose.yml` primeiro.
- **Erro de conexão com o banco ao rodar o uvicorn** — confirme que o
  Docker Desktop está aberto e que `docker ps` mostra um container
  Postgres rodando.
- **Erro de autenticação da Claude API** — confirme que
  `ANTHROPIC_API_KEY` está preenchida no `.env` (não no
  `.env.example`) e que a chave tem créditos disponíveis no console da
  Anthropic.
