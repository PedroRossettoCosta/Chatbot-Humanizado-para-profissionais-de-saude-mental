# Modelo de dados

As tabelas do MarIA, o que cada uma guarda e por quê. O código vive em
[`backend/app/models.py`](../../backend/app/models.py).

---

## Visão geral

```
User ── UserSession                  quem entra no painel (conta Google) e suas sessões
  │
  └─(professional_id)─┐
                      ▼
Professional ──┬── Document          documentos da base de conhecimento
               │
               ├── Contact           quem fala com o bot
               │     └── Conversation        uma thread de atendimento
               │           ├── Message              cada mensagem
               │           ├── SafetyAlert          disparo da triagem
               │           │     └── SafetyAlertEvent   trilha de auditoria
               │           └── Appointment       pré-agendamento
               │
               └── Conversation      (atalho para listar por profissional)
```

Convenções usadas em todas as tabelas:

- **Chave primária** é um UUID em texto, gerado pela aplicação. Isso
  evita expor um contador sequencial (que revelaria quantos pacientes a
  profissional tem) e permite gerar o id antes de gravar.
- **Datas** são `TIMESTAMP WITH TIME ZONE`, sempre em UTC. A conversão
  para o horário de Brasília acontece na exibição, o que evita
  ambiguidade em horário de verão e em agendamentos.
- **Valores fixos** (canal, estado, nível de alerta) são texto, com as
  opções válidas declaradas como `StrEnum` no código. Texto simples
  facilita a evolução do schema; a validação fica na aplicação.
- **Dados pessoais** usam o tipo `EncryptedText`, que cifra ao gravar e
  decifra ao ler, de forma transparente.

---

## Professional

A profissional dona da conta. É a raiz do isolamento multi-tenant.

| Campo | Tipo | Observação |
|---|---|---|
| `id` | UUID | |
| `slug` | texto, único | Identificador legível (`marilia`), usado nas rotas |
| `name` | texto | Nome exibido ao paciente |
| `voice_tone` | texto | Instrução de tom, injetada no prompt |
| `audience_description` | texto, opcional | Especialidade e público. Vai sempre no prompt de resposta (para a MarIA apresentar a profissional) e calibra a triagem |
| `service_info` | texto, opcional | Atendimento e valores. Sempre no prompt, porque o preço é respondido na primeira pergunta |
| `voice_examples` | JSON, opcional | Resposta boa e ruim para cada uma das 3 perguntas fixas (`services/guidelines.py`) |
| `extra_never_say` | JSON, opcional | Itens de "nunca dizer" da profissional, somados aos fixos do produto |
| `calendar_id` | texto, opcional | Agenda do Google usada no pré-agendamento |
| `alert_email` | texto, opcional | Onde ela recebe os alertas por e-mail. Quem envia é a conta do produto (SMTP no `.env`) |
| `in_session_since` | data, opcional | Botão "Em consulta" ligado desde. Nulo = desligado |
| `in_session_until` | data, opcional | Fim automático do "Em consulta". Nulo com `in_session_since` preenchido = até ela desligar |
| `pronouns` | texto, opcional | Como a MarIA fala dela com o paciente: `feminine`, `masculine` ou `neutral` (`guidelines.PRONOUNS`). Nulo = neutro |
| `session_minutes` | inteiro, opcional | Duração da sessão (15 a 240). A agenda usa para montar os horários |
| `onboarding_step` | inteiro, opcional | Etapa do cadastro alcançada (1 a 7), para voltar de onde parou |
| `rules_accepted_at` | data, opcional | Quando ela leu e aceitou as regras fixas da MarIA |
| `onboarding_completed_at` | data, opcional | Cadastro concluído. Nulo = o painel mostra o cadastro |
| `created_at` | data | |

`calendar_id` fica por profissional para que cada uma exponha só a
agenda que quiser, em vez de dar acesso à agenda pessoal inteira.

## Document

Registro de um arquivo enviado para a base de conhecimento. O **texto
não fica aqui** — ele é dividido em trechos e indexado no ChromaDB. Esta
tabela guarda o que o painel precisa listar.

| Campo | Tipo | Observação |
|---|---|---|
| `id` | UUID | |
| `professional_id` | UUID | |
| `filename` | texto | |
| `content_type` | texto | |
| `chunk_count` | inteiro | Em quantos trechos o arquivo foi dividido |
| `uploaded_at` | data | |

## Contact

Quem conversa com o bot, do outro lado do canal.

| Campo | Tipo | Observação |
|---|---|---|
| `id` | UUID | |
| `professional_id` | UUID | |
| `channel` | texto | `whatsapp` ou `simulator` |
| `external_id` | **cifrado** | O telefone no WhatsApp; o id de sessão no simulador |
| `external_id_index` | texto, indexado | Índice cego, para busca |
| `display_name` | **cifrado**, opcional | Nome do perfil informado pelo canal |
| `created_at` | data | |

**Restrição de unicidade:** (`professional_id`, `channel`,
`external_id_index`). O mesmo número, no mesmo canal, é sempre o mesmo
contato — mas dentro da conta daquela profissional. Se duas
profissionais atenderem a mesma pessoa, são dois contatos separados, e
nenhuma enxerga a conversa da outra.

### Por que existe o índice cego

O telefone é cifrado, e a cifra é diferente a cada gravação (é o que
impede descobrir que duas conversas são da mesma pessoa só olhando o
banco). O efeito colateral é que não dá para procurar por ele.

A solução é guardar, ao lado, uma impressão digital determinística do
valor — um HMAC-SHA256 com a chave secreta. O mesmo telefone sempre gera
o mesmo índice, então a busca funciona; e sem a chave, não dá para
partir do índice e chegar ao número. O HMAC (e não um hash simples) é
necessário porque a quantidade de telefones possíveis é pequena o
bastante para ser varrida por força bruta.

## Conversation

Uma thread de atendimento entre um contato e a profissional.

| Campo | Tipo | Observação |
|---|---|---|
| `id` | UUID | |
| `professional_id` | UUID | |
| `contact_id` | UUID | |
| `state` | texto | `active`, `human` ou `emergency_hold` |
| `needs_attention` | booleano | Marcação "necessita atenção da profissional" (sinal da triagem) |
| `awaiting_reply_since` | data, opcional | "Aguardando você": a pessoa pediu a profissional ou recusou o bot, e ainda não teve resposta |
| `last_contact_message_at` | data, opcional | Última mensagem do contato; conta a janela de 24h do WhatsApp |
| `contact_type` | texto | `lead` ou `patient` |
| `created_at` | data | |
| `last_message_at` | data | Base do corte da política de retenção e da ordem da lista de Conversas |

### Os três estados

| Estado | O que significa |
|---|---|
| `active` | O bot responde normalmente |
| `human` | A profissional assumiu pelo painel; o bot fica em silêncio |
| `emergency_hold` | A triagem detectou risco; o fluxo normal está interrompido |

`needs_attention` é **separado do estado** de propósito. Ele representa
o segundo nível de triagem, o sofrimento intenso: a profissional é
avisada, mas o bot continua atendendo normalmente. Misturar isso com o
estado faria o sistema parar de responder em situações em que a
profissional pediu explicitamente que ele continuasse.

`awaiting_reply_since` também fica fora do estado: com "Em consulta"
ligado, a pessoa que pediu a profissional continua sendo atendida pela
MarIA (`active`), mas está esperando por ela. É uma data, e não um
booleano, para a tela mostrar desde quando.

`contact_type` existe porque a profissional pediu retenção diferente
para quem virou paciente e para quem ficou só como lead. Hoje a política
é uniforme; o campo já está aqui para não exigir migração depois.

## Message

Cada mensagem trocada. O conteúdo é sempre cifrado em repouso.

| Campo | Tipo | Observação |
|---|---|---|
| `id` | UUID | |
| `seq` | inteiro, automático | Ordem de inserção, gerada pelo banco |
| `conversation_id` | UUID | |
| `role` | texto | `user` ou `assistant` |
| `content` | **cifrado** | |
| `sent_by` | texto, opcional | `bot`, `professional` ou `system` |
| `external_id` | texto, único, opcional | Id da mensagem no canal de origem |
| `created_at` | data | |

`role` usa o mesmo vocabulário da API da Claude, então o histórico é
montado sem tradução.

### Por que a ordem não vem do horário

O caminho natural seria ordenar o histórico por `created_at`. Isso
falha: o relógio do sistema tem resolução de milissegundos, e no Windows
chegou a devolver o **mesmo** horário para cinco chamadas seguidas.
Mensagens que chegam em rajada — como os fragmentos que o WhatsApp
envia quando alguém digita em partes — empatariam, e `ORDER BY
created_at` devolveria a conversa fora de ordem.

O efeito seria silencioso e ruim: o modelo receberia o diálogo
embaralhado e responderia com base em um contexto errado.

Por isso `seq` é um contador gerado pelo próprio PostgreSQL, imune ao
relógio, e é ele que ordena o histórico. `created_at` continua existindo
para exibição e para a política de retenção.

`sent_by` só é preenchido na saída, e responde a uma pergunta que `role`
não responde: **quem escreveu**. Uma mensagem com `role=assistant` pode
ter vindo do bot, da profissional respondendo pelo painel, ou ser um
texto fixo do sistema (o aviso de IA, a mensagem de emergência). O
painel precisa dessa distinção para mostrar a conversa corretamente.

`external_id` é único porque a Meta reenvia o mesmo webhook quando não
recebe confirmação. Sem essa restrição, o paciente receberia duas
respostas para a mesma mensagem.

## SafetyAlert

Um disparo da triagem de segurança. **Imutável depois de criado.**

| Campo | Tipo | Observação |
|---|---|---|
| `id` | UUID | |
| `professional_id` | UUID | |
| `conversation_id` | UUID | |
| `message_id` | UUID, opcional | Mensagem que disparou |
| `level` | texto | `emergency`, `possible_risk` ou `bot_refused` (a pessoa recusou falar com o bot; não é risco e fica fora das métricas da triagem) |
| `excerpt` | **cifrado**, opcional | Trecho que motivou o disparo |
| `created_at` | data | |

Os dois níveis vêm diretamente da entrevista de protocolo com a
profissional. A distinção é essencial: no nicho dela, mensagens de
sofrimento relacional intenso são comuns e **não** devem acionar o
protocolo de emergência. Ver
[Segurança e LGPD](seguranca-lgpd.md).

`excerpt` existe para a profissional entender por que o alerta disparou
sem precisar abrir a conversa inteira.

`message_id` é opcional porque a mensagem pode ser apagada pela política
de retenção antes do alerta ser revisado.

## SafetyAlertEvent

A trilha de auditoria de um alerta. Só acrescenta linhas, nunca altera.

| Campo | Tipo | Observação |
|---|---|---|
| `id` | UUID | |
| `alert_id` | UUID | |
| `event_type` | texto | `viewed`, `reviewed`, `notified`, `notify_failed` (o e-mail do alerta não saiu; a nota diz o motivo) ou `bot_released` (a profissional devolveu a conversa ao bot) |
| `actor` | texto | `system` ou o id da profissional |
| `note` | texto, opcional | |
| `created_at` | data | |

### Por que a situação do alerta não é uma coluna

O caminho óbvio seria uma coluna `revisado` no próprio alerta. O
requisito, porém, é que a profissional **não consiga apagar nem alterar**
um alerta, apenas marcá-lo como revisado (RNF05 em
[requisitos](../levantamento-requisitos-mvp.md)).

Com eventos separados, a situação atual é derivada do histórico, e o
histórico é somente-acréscimo. Isso preserva *quando* disparou, *quando*
ela viu e *quando* revisou. Uma coluna sobrescrita perderia tudo isso, e
é justamente esse registro que a profissional pediu para poder avaliar
depois se o sistema classificou certo.

## Appointment

Um pré-agendamento criado pelo bot e espelhado no Google Calendar.

| Campo | Tipo | Observação |
|---|---|---|
| `id` | UUID | |
| `professional_id` | UUID | |
| `conversation_id` | UUID | |
| `calendar_id` | texto, opcional | Agenda onde o evento foi criado |
| `calendar_event_id` | texto, opcional | Id do evento no Google |
| `starts_at` / `ends_at` | data | |
| `status` | texto | `tentative`, `confirmed` ou `cancelled` |
| `created_at` | data | |

O bot cria sempre como `tentative` (provisório). A confirmação é um ato
da profissional, no painel — o sistema nunca fecha um horário sozinho.

`calendar_id` é repetido aqui, e não só em `Professional`, para o evento
continuar rastreável se a profissional trocar de agenda depois.

---

## User

Quem entra no painel, identificado pela conta Google. Separado de
`Professional` porque são coisas diferentes: a conta é quem faz login;
a profissional é o consultório que a MarIA atende. No MVP é uma para
uma, e um dia pode haver mais de uma pessoa por consultório.

| Campo | Tipo | Observação |
|---|---|---|
| `google_sub` | texto, único | Identificador permanente da conta no Google. O e-mail pode mudar; ele, não |
| `email` | texto | Conferido contra a lista de convidados a cada requisição |
| `name`, `picture_url` | texto | Vêm do Google a cada login |
| `professional_id` | FK, único, nulo | Nulo até o cadastro ser concluído |
| `created_at`, `last_login_at` | data | |

Não há senha: quem prova a identidade é o Google.

## UserSession

Uma sessão de login. O navegador guarda um código aleatório num cookie
`httpOnly`; a tabela guarda só o **hash** dele (`token_hash`), então
quem ler o banco não consegue se passar pela profissional.

| Campo | Tipo | Observação |
|---|---|---|
| `user_id` | FK | Apagada junto com a conta |
| `token_hash` | texto, único | SHA-256 do código do cookie |
| `expires_at` | data | Padrão: 7 dias depois do login (`SESSION_DAYS`) |

Sair apaga a linha. Uma sessão vencida é apagada na próxima vez que
aparece.

---

## O que este modelo ainda não cobre

Campos específicos do WhatsApp, deixados de fora deliberadamente na
primeira versão e a rever antes da integração:

- Qual dos nossos números recebeu a mensagem (roteamento multi-tenant)
- Tipo da mensagem (imagem, áudio, documento)
- Situação de entrega (entregue, lida, falhou)
