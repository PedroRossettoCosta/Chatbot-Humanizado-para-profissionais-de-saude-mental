# Desenvolvimento

Instalar, rodar, testar e mexer no banco. Os comandos estão no formato
do Windows (PowerShell); em Linux ou macOS, troque
`.venv\Scripts\activate` por `source .venv/bin/activate` e `copy` por
`cp`.

---

## 1. Primeira vez na máquina

Pré-requisitos: [Docker Desktop](https://www.docker.com/products/docker-desktop/),
Python 3.12, Node.js 18+.

### Banco de dados

A partir da raiz do repositório:

```bash
docker compose up -d
```

Isso sobe um PostgreSQL 16 em segundo plano, escutando em
`localhost:5432`. O Docker Desktop precisa estar aberto, mas nenhum
terminal precisa ficar aberto — o contêiner continua rodando sozinho.

### Backend

```bash
cd backend
copy .env.example .env
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Agora preencha o `.env`. As chaves e como obtê-las estão em
[Configuração](configuracao.md). O mínimo para subir a aplicação é
`ANTHROPIC_API_KEY` e `DATA_ENCRYPTION_KEY`.

Crie as tabelas:

```bash
alembic upgrade head
```

E rode a API:

```bash
uvicorn app.main:app --reload
```

Deve aparecer `Application startup complete`. A API fica em
`http://127.0.0.1:8000` e a documentação interativa em
`http://127.0.0.1:8000/docs`.

### Front-end

Em outro terminal, a partir da raiz:

```bash
cd frontend
copy .env.example .env
npm install
npm run dev
```

O painel abre em `http://localhost:5173` e chama a API em `/api`
(o Vite repassa para `http://127.0.0.1:8000`). Para entrar, o
`backend/.env` precisa de `GOOGLE_CLIENT_ID` e do seu e-mail em
`ALLOWED_EMAILS`.

O visual segue o protótipo (`Documentation/TCC App Design/`), com
Tailwind e as cores dele em `src/index.css`. O "preflight" do Tailwind
fica desligado até o painel inteiro estar no visual novo.

## 2. No dia a dia

No Windows, com o Docker Desktop aberto, dê dois cliques em
`iniciar.bat` (na raiz). Ele sobe o banco, aplica as migrações, encerra
servidores antigos presos nas portas 8000 e 5173, abre a API e o painel
em duas janelas e o navegador na tela de login (`http://localhost:5173/?sair`, que
encerra a sessão salva). Para parar,
feche as duas janelas.

À mão, são dois terminais, a partir da raiz:

```bash
docker compose up -d
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload
```

```bash
cd frontend
npm run dev
```

Para parar: `Ctrl+C` em cada um. O contêiner do PostgreSQL continua
rodando até você executar `docker compose down` ou fechar o Docker
Desktop.

Depois de dar `git pull`, vale rodar `alembic upgrade head` — se alguém
mexeu no banco, é isso que deixa o seu igual.

## 3. Migrações do banco (Alembic)

### Por que existe

A estrutura do banco (quais tabelas e colunas existem) e o código Python
que a descreve são duas coisas separadas. Editar `models.py` **não muda
o PostgreSQL**: o arquivo muda, o banco continua como estava.

O Alembic é o que mantém os dois em sincronia. Ele funciona como o Git,
mas para a estrutura do banco: cada mudança vira um arquivo em
`alembic/versions/`, com instruções para aplicar (`upgrade`) e para
desfazer (`downgrade`). Esses arquivos são versionados junto com o
código, e o banco guarda internamente em qual migração ele está.

### Comandos

Todos de dentro de `backend/`, com o venv ativado.

| Comando | O que faz |
|---|---|
| `alembic upgrade head` | Aplica tudo que falta. É o comando do dia a dia |
| `alembic current` | Mostra em qual migração este banco está |
| `alembic history` | Lista as migrações, da mais antiga à mais nova |
| `alembic downgrade -1` | Desfaz a última migração |
| `alembic revision --autogenerate -m "descrição"` | Cria uma migração comparando os modelos com o banco |

### Mudando uma tabela

1. Edite `app/models.py`.
2. Gere a migração:
   ```bash
   alembic revision --autogenerate -m "adiciona campo tal"
   ```
3. **Abra o arquivo gerado em `alembic/versions/` e confira.** O
   autogenerate é bom, mas não é infalível: ele costuma errar em
   renomeações (que ele vê como "apagar uma coluna e criar outra",
   perdendo os dados) e não detecta mudanças só de valores permitidos.
4. Aplique:
   ```bash
   alembic upgrade head
   ```
5. Commite o arquivo da migração junto com a mudança em `models.py`.

> A aplicação **não cria tabelas** ao subir. Isso é proposital: se o
> `create_all` continuasse ligado, ele criaria tabelas por fora do
> controle do Alembic e os dois acabariam divergindo.

## 4. Testes

Precisam do PostgreSQL rodando, porque parte deles conversa com o banco
de verdade. De dentro de `backend/`, com o venv ativado:

```bash
pytest
```

Outras formas úteis:

```bash
pytest -v                         # mostra cada teste
pytest tests/test_crypto.py       # só um arquivo
pytest -k blind_index             # só os testes cujo nome casa
```

### O que está coberto

| Arquivo | Cobre |
|---|---|
| `test_crypto.py` | Cifragem, decifragem e índice cego |
| `test_conversations.py` | Contato reaproveitado, isolamento por canal, cifragem em repouso, histórico |
| `test_professionals_api.py` | Cadastro, slug duplicado, slug inválido |
| `test_text_extraction.py` | Divisão do texto em trechos |
| `test_chat_disclaimer.py` | Aviso de IA na primeira mensagem, e não nas seguintes |
| `test_triage_rules.py` | Camada 1 da triagem: frases que disparam e as que não podem disparar |
| `test_triage_layers.py` | Camadas 1 + 2: o modelo só sobe o nível, falha fechada |
| `test_chat_triage.py` | Triagem no fluxo do chat: texto de emergência, alerta, bot em silêncio |
| `test_reply_prompt.py` | Montagem do prompt: nome MarIA, lista fixa, regras da profissional |
| `test_handoff.py` | Pedido de humano, recusa do bot, "Em consulta", assumir e devolver |
| `test_notifications.py` | E-mail de alerta: quando envia, sem conteúdo da conversa, falhas registradas |
| `test_onboarding.py` | Cadastro em etapas: etapa salva, duração, o que falta, aceite das regras e conclusão |
| `test_auth.py` | Login com Google, convite, sessão, rotas fechadas sem login, isolamento entre profissionais, limite de tentativas |

Os testes que chamariam a API da Claude usam `monkeypatch` para
substituir a chamada, e o envio de e-mail é sempre substituído em
`conftest.py`. Nenhum teste gasta crédito, envia e-mail ou depende de rede.

O cliente `client` entra como uma conta de teste dona de qualquer
profissional, para os testes das funcionalidades não dependerem do
login. O login e a checagem de dono de verdade usam `anon_client`, em
`test_auth.py`, com o token do Google substituído.

Eles criam e apagam seus próprios dados, com slugs começando em
`test-pytest-`. Ainda assim, **rode sempre contra o banco local**, nunca
contra um banco com dados reais.

## 5. Retenção de dados

Apaga conversas sem atividade há mais de `DATA_RETENTION_DAYS` (padrão:
90). É manual, não agendado:

```bash
python scripts/purge_old_conversations.py
```

## 6. Problemas comuns

**`docker compose up -d` diz "no configuration file provided"**
Você não está na pasta certa. O comando roda na raiz do repositório,
onde fica o `docker-compose.yml`.

**Erro de conexão com o banco ao subir a API**
O Docker Desktop está aberto? `docker compose ps` deve listar o
contêiner do PostgreSQL. Se não listar, rode `docker compose up -d`.

**`ModuleNotFoundError` ou versão errada do Python**
O venv não está ativado — o prompt do terminal deve começar com
`(.venv)`. Se a ativação falhar em silêncio no PowerShell, rode
`python -m uvicorn app.main:app --reload`, que ignora o `PATH` e usa o
Python do venv.

**"Extra inputs are not permitted" ao subir**
Existe uma variável no `.env` que a aplicação não conhece. Toda
variável precisa estar declarada em `app/config.py`.

**O front-end mostra "Failed to fetch"**
Ou a API não está rodando, ou o front-end subiu em outra porta. O Vite
usa a 5174 quando a 5173 está ocupada, e aí o CORS bloqueia. Confira se
`FRONTEND_URL` no `.env` do backend bate com a porta que apareceu no
terminal do front-end.

**Erro de autenticação da Claude**
Confira se `ANTHROPIC_API_KEY` está preenchida no `.env` (não no
`.env.example`) e se a conta tem créditos.
