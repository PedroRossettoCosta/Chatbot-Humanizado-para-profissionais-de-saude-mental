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
uvicorn app.main:app --reload --reload-dir app
```

O `--reload-dir app` é obrigatório: sem ele o reload observa o
`backend/` inteiro e reinicia a API sem parar (ver "A SelenIA não
responde no WhatsApp" em Problemas comuns).

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

No Windows, dê dois cliques em `iniciar.bat` (na raiz). Ele também
serve para uma máquina nova (ex.: o notebook), desde que Docker
Desktop, Python 3.12 e Node.js estejam instalados: cria o
`backend\.venv`, instala os pacotes do Python e do Node (e reinstala
sozinho quando `requirements.txt` ou `package-lock.json` mudam, depois
de um `git pull`), copia os `.env.example` e gera uma
`DATA_ENCRYPTION_KEY` nova. As outras chaves do `backend\.env` não
estão no Git: copie o `.env` da outra máquina ou preencha pelo menos
`ANTHROPIC_API_KEY`, `GOOGLE_CLIENT_ID` e `ALLOWED_EMAILS` (o script
abre o arquivo no Bloco de Notas). O domínio fixo do ngrok só funciona
em uma máquina por vez.

Em toda execução, ele abre o Docker Desktop se estiver fechado, sobe o
banco e espera ele ficar pronto, aplica as migrações, encerra
servidores antigos presos nas portas 8000 e 5173, abre a API, o painel
e o túnel do WhatsApp (ngrok, se estiver instalado e com
`PUBLIC_WEBHOOK_HOST` no `.env`) em janelas próprias, e o navegador na
tela de login (`http://localhost:5173/?sair`, que encerra a sessão
salva). Para parar, feche as janelas.

À mão, são dois terminais, a partir da raiz:

```bash
docker compose up -d
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload --reload-dir app
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
| `test_webhook.py` | WhatsApp: desafio da Meta, assinatura, aviso de IA e resposta, id da Meta guardado na mensagem enviada, recusa da Meta marcada como não entregue, reenvio, número sem profissional, emergência na hora, áudio, mensagens quebradas, espera recomeçada, resposta do painel pela Meta, filtro do túnel, foto/áudio/documento com só a referência guardada, arquivo buscado na Meta na hora, documento desconhecido como download, arquivo expirado, mídia de outra mensagem |
| `test_triage_fragments.py` | Frase de risco quebrada em várias mensagens: junta, não repete alerta, o mais grave ganha, respeita os 5 minutos |
| `test_chat_triage.py` | Triagem no fluxo do chat: texto de emergência, alerta, bot em silêncio; a camada 2 só recebe as últimas 3 mensagens em até 5 minutos; a resposta esquece risco com mais de 5 minutos |
| `test_reply_prompt.py` | Montagem do prompt: nome SelenIA, lista fixa, regras da profissional, formas de pagamento, nada de "vou perguntar" sem `avisar_profissional`, "paciente especial" não dá permissão |
| `test_handoff.py` | Pedido de humano, recusa do bot, "Em consulta", assumir e devolver |
| `test_notifications.py` | E-mail de alerta: quando envia, sem conteúdo da conversa, falhas registradas; pedido levado pela SelenIA (`avisar_profissional`): e-mail uma vez, por motivo, bot continua, responder limpa |
| `test_clients.py` | Clientes e dias especiais: dia especial abre o dia todo, cada cliente com os seus dias, limite por dia não vale para quem tem permissão, permissão só com cliente ativo, a SelenIA só vê o horário especial pela permissão do painel, confirmar sessão torna ativo, tirar e pôr na lista, validação de dias especiais e formas de pagamento |
| `test_onboarding.py` | Cadastro em etapas: etapa salva, duração, o que falta, aceite das regras e conclusão |
| `test_alerts_api.py` | Tela de Alertas: ordem da lista, trilha, visto e revisado uma vez só, liberação na trilha, sem rota de editar ou apagar |
| `test_contact_limit.py` | Limite de mensagens por hora, por pessoa: resposta até o limite, aviso uma vez e silêncio sem chamar o modelo, camada 1 pegando risco acima do limite, outra pessoa não afetada, volta quando a hora passa |
| `test_whatsapp_numbers.py` | Conectar o número: formatos, fluxo até o registro, código errado, reenvio por ligação, número já na conta ou já verificado, limite de registros, bloqueio da Meta, número de outra conta, cancelar, servidor sem WABA (Graph API simulada), volta para o código quando a Meta diz que o número não está verificado, trocar o nome, aplicar o nome aprovado, desconectar para trocar o número |
| `test_reply_refusal.py` | Recusa do modelo: resposta sem texto vira texto fixo e marca a conversa |
| `test_usage.py` | Uso de tokens: uma linha por chamada (resposta e triagem) sem conteúdo, parte fixa do prompt com cache, nada anotado fora de `collect_usage` |
| `test_inbox.py` | Tela de Conversas: ordem da lista, "Aguardando você", e-mail de pedido uma vez só, janela de 24h, número mascarado |
| `test_documents_api.py` | Envio e remoção de documento da base de conhecimento |
| `test_auth.py` | Login com Google, convite, sessão, rotas fechadas sem login, isolamento entre profissionais, limite de tentativas |
| `test_appointments.py` | Pedidos de horário: reserva provisória, horário ocupado, duas pessoas ao mesmo tempo (threads e banco de verdade), índice único, troca de horário no mesmo dia, uma sessão por dia por pessoa (vários dias permitidos), teto de pedidos pendentes por pessoa, remarcar e cancelar como pedido, pedido vencido, limite por dia, confirmar e recusar com e sem janela do WhatsApp, lista, ferramenta só com permissão de eventos, sessão e compromisso marcados pelo painel, calendário da semana |
| `test_calendar.py` | Agenda: cálculo dos horários livres (antecedência, ocupado, duração, fim de semana), validação do horário de atendimento, conexão com o Google (permissão desmarcada, acesso cifrado, desconectar revoga), ferramenta da SelenIA e falha do Google |

Os testes que chamariam a API da Claude usam `monkeypatch` para
substituir a chamada, e o envio de e-mail e as chamadas à API da Meta
são sempre substituídos em `conftest.py`. Nenhum teste gasta crédito,
envia e-mail ou mensagem, ou depende de rede. A agenda também: a troca
do código, o livre/ocupado, os eventos e a revogação do Google são
substituídos em `test_calendar.py` e `test_appointments.py`.

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

## 6. Backup e custo

Backup do banco (arquivo em `backend/backups/`, fora do git) e teste de
restauração numa base separada (`<nome>_restauracao`), que compara a
contagem de linhas de cada tabela com a original. Usa o `pg_dump` do
contêiner quando a máquina não tem o do Postgres:

```bash
python scripts/backup.py
python scripts/backup.py --restaurar backups/maria-AAAAMMDD-HHMM.dump
```

O backup leva as conversas cifradas; a chave fica no `.env` e não vai
junto. Primeiro teste de restauração: 12/10/2026, todas as tabelas
batendo.

Custo real do modelo, a partir dos tokens gravados em `llm_usage`:

```bash
python scripts/custo.py --dias 30 --dolar 5.50
```

## 6b. Avaliação do modelo (fora do pytest)

Chamam a API da Claude de verdade e custam dinheiro; por isso não
rodam com o `pytest`. Rode a partir de `backend/`:

```bash
python -m scripts.avaliar_triagem                   # triagem x rótulos da Marília
python -m scripts.avaliar_respostas                 # prompt injection e respostas sensíveis
python -m scripts.avaliar_respostas sensiveis S15   # só alguns casos
```

`avaliar_respostas` passa cada caso pelo caminho de uma conversa real
(aviso de IA, triagem, handoff, resposta), com um perfil fictício e sem
banco, e um segundo modelo (juiz) diz se a resposta cumpre o critério
do caso. O relatório, com todas as conversas, o custo e a leitura do
cache, vai para `Documentation/resultados-testes/`. O juiz é apoio: leia
as falhas e as dúvidas antes de mudar o prompt.

## 7. Problemas comuns

**`docker compose up -d` diz "no configuration file provided"**
Você não está na pasta certa. O comando roda na raiz do repositório,
onde fica o `docker-compose.yml`.

**Erro de conexão com o banco ao subir a API**
O Docker Desktop está aberto? `docker compose ps` deve listar o
contêiner do PostgreSQL. Se não listar, rode `docker compose up -d`.

**`ModuleNotFoundError` ou versão errada do Python**
O venv não está ativado — o prompt do terminal deve começar com
`(.venv)`. Se a ativação falhar em silêncio no PowerShell, rode
`python -m uvicorn app.main:app --reload --reload-dir app`, que ignora
o `PATH` e usa o Python do venv.

**`No module named 'psycopg'` ao aplicar as migrações**
O SQLAlchemy 2.1 passou a escolher o driver `psycopg` (versão 3) para
uma `DATABASE_URL` que começa só com `postgresql://`, e o projeto
instala o `psycopg2`. A URL precisa dizer o driver:
`postgresql+psycopg2://...`, como no `.env.example` desde 30/09/2026.
Em um `.env` antigo, troque o começo da linha à mão.

**A SelenIA não responde no WhatsApp (mas o simulador responde)**
Confira se a API está reiniciando sozinha: na janela "SelenIA - API",
aparece `WatchFiles detected changes` e `Started server process` de
poucos em poucos segundos. Cada início da API abre o ChromaDB, que
grava em `backend/chroma_data/`; se o reload observa o `backend/`
inteiro, essa gravação reinicia a API, que abre o ChromaDB de novo, e
assim sem parar. A resposta do WhatsApp espera 6 segundos para juntar
mensagens quebradas e se perde a cada reinício. O `iniciar.bat` usa
`--reload-dir app` desde 30/09/2026; à mão, use o mesmo.

**A API continua com código ou `.env` antigos depois de reiniciar**
No Windows, o `--reload` do uvicorn às vezes deixa um processo filho
vivo depois que o principal morre, e ele continua atendendo na porta
8000 com o que tinha carregado. O `netstat` mostra o PID do principal,
que já não existe. O `iniciar.bat` encerra esses órfãos (desde
28/09/2026); à mão, feche as janelas da API e procure processos
`python.exe` com `spawn_main(parent_pid=...)` cujo pai não existe mais.
Mudança no `.env` sempre pede reinício: o reload só observa a pasta
`app/`.

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
