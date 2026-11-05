# SelenIA

Assistente virtual humanizado para o atendimento inicial de
profissionais autônomos de saúde mental (psicólogas, psicanalistas).

O SelenIA responde às primeiras mensagens de quem procura a profissional:
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
perfil e regras da SelenIA, handoff e "Em consulta", alerta por e-mail).

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
uvicorn app.main:app --reload --reload-dir app

# 3. Front-end (em outro terminal, a partir da raiz)
cd frontend
copy .env.example .env
npm install
npm run dev
```

No Windows, dá para pular tudo isso: com Docker Desktop, Python 3.12 e
Node.js instalados, dê dois cliques em `iniciar.bat`. Na primeira vez
ele cria o venv, instala os pacotes e o `.env`; em toda vez, abre o
Docker Desktop se estiver fechado, sobe o banco, a API e o painel e
abre o navegador.

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
  quatro níveis, texto fixo de emergência e falha fechada, inclusive
  para frase de risco quebrada em várias mensagens.
- **Perfil e regras da SelenIA**: tom de voz, exemplos, valores na
  primeira resposta e a lista fixa do que ela nunca diz.
- **Handoff**: a profissional assume, responde e devolve ao bot; pedido
  de humano, recusa do bot e "Em consulta", que liga sozinho pelo Google
  Agenda (ou pelo botão), diz ao contato até que horas ela atende e
  junta os e-mails de pedido num resumo no fim da consulta.
- **Alerta por e-mail** para a profissional, sem conteúdo da conversa;
  também quando alguém pede para falar com ela ou quando a SelenIA leva
  um pedido que só ela decide (`avisar_profissional`: horário fora do
  expediente, pagamento, desconto), sem parar o bot.
- **Clientes**: lista de clientes ativos (entra sozinho ao confirmar uma
  sessão), tirar e pôr na lista, e permissão para marcar nos horários
  especiais, fora do expediente, que a profissional define.
- **Formas de pagamento** obrigatórias no cadastro e no Perfil (escolha múltipla), informadas pela
  SelenIA quando perguntam como pagar.
- **Login com Google**, só para e-mails convidados, com todas as rotas
  de gestão protegidas e cada profissional vendo só os próprios dados.
- **Cadastro em 7 etapas** no primeiro acesso, no visual do protótipo,
  com aceite das regras da SelenIA.
- **Conectar o WhatsApp pelo painel** (etapa 6 e tela WhatsApp do menu): número, código
  por SMS ou ligação e registro na Meta (testado de verdade em 19/10);
  depois de conectado, trocar o nome que aparece ou trocar o número.
- **Painel** no visual do protótipo: menu, "Em consulta" no topo,
  Perfil do atendimento, Base de conhecimento (enviar e remover
  documentos) e o simulador "Testar a SelenIA", com o que a triagem
  decidiu em cada resposta.
- **Conversas** no computador e no celular: quem precisa da
  profissional primeiro ("Aguardando você", emergência, atenção),
  assumir, responder, devolver à SelenIA e a janela de 24h do WhatsApp.
- **Alertas** com a trilha de auditoria (disparo, o que a SelenIA fez,
  e-mail, visto, revisado, liberação), sem editar nem apagar, e o
  número de alertas sem revisar no menu.
- **LGPD básico**: conteúdo das mensagens e dados de contato cifrados em
  repouso, aviso automático de que é uma IA, política de retenção.
- **WhatsApp**: fotos, áudios e documentos aparecem na conversa do painel (buscados na Meta na hora, sem guardar). Webhook com assinatura conferida, triagem assim que a
  mensagem chega, espera de alguns segundos para juntar mensagens
  quebradas, resposta pela API da Meta, resposta do painel enviada ao
  WhatsApp e túnel fixo (ngrok) que só deixa passar o webhook. Falta
  publicar o app da Meta para chegarem mensagens reais.
- **Agenda**: a profissional conecta o Google Agenda pelo painel e
  informa o horário de atendimento; a SelenIA oferece até 3 horários
  livres e reserva provisoriamente o que a pessoa escolher; a
  profissional confirma ou recusa no painel (24h de validade), e a
  pessoa recebe a resposta pela conversa. Remarcar e cancelar também
  vão pela conversa, sempre como pedido que a profissional confirma.
- **Limites por pessoa**: até 4 pedidos de horário aguardando
  confirmação e 50 mensagens por hora; acima disso, a SelenIA pausa as
  respostas àquela pessoa (a triagem por regras continua) e marca a
  conversa para a profissional.
- **Custo medido**: tokens de cada chamada ao modelo gravados sem
  conteúdo, resumo em dólar e reais (`scripts/custo.py`), e cache da
  parte fixa do prompt.
- **Backup** do banco com restauração testada (`scripts/backup.py`).
- **Testes de comportamento** no modelo real: 22 ataques de prompt
  injection e 31 mensagens sensíveis, com relatório
  (`scripts/avaliar_respostas.py`); se o modelo recusar a resposta, a
  pessoa recebe um texto fixo em vez de mensagem vazia.
- **Mensagem não entregue**: se a Meta recusar um envio, a mensagem
  aparece com "Não entregue" na tela Conversas.

Em construção, na ordem do
[plano do MVP](Documentation/planejamento-mvp-9out.md):

- Publicação do app na Meta (política de privacidade) e teste com mensagens reais
- Textos fixos da agenda aprovados pela Marília

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
