# Agenda

> Situação: funcionando; textos fixos de confirmação e recusa sem aprovação da Marília. Última atualização: 28/09/2026.

## O que é

Na tela **Agenda**, a profissional conecta o Google Agenda dela e diz em
que dias e horários atende. Quando alguém quer marcar na conversa, a
MarIA consulta a agenda, oferece até 3 horários livres e, quando a
pessoa escolhe, **reserva o horário provisoriamente** ("Sessão (a
confirmar)" na agenda). A profissional confirma ou recusa na mesma
tela, e a pessoa recebe a resposta pela conversa. Nada fica confirmado
sem ela.

A tela também mostra o **calendário da semana** (os eventos do Google
Agenda, as sessões e o horário de atendimento), onde ela marca sessões
ou outros compromissos direto no Google.

## Por que existe

Perguntar "tem horário?" é das primeiras coisas que alguém faz ao
procurar atendimento, e a MarIA não sabia responder.

- **20/09/2026:** decidido usar o Google Calendar com uma conta de
  serviço (a profissional compartilharia a agenda com o e-mail dela).
- **28/09/2026 (Pedro):** trocado pela conexão no próprio painel. A
  profissional clica em "Sincronizar com o Google Agenda", escolhe a
  conta na janela do Google e pronto, sem copiar ID de agenda nem mexer
  no compartilhamento. O horário de atendimento fica no banco, para a
  MarIA consultar.
- **Permissão mínima para ler (28/09/2026):** só livre/ocupado. Para
  oferecer horário basta saber o que está ocupado; o nome de um evento
  pode ser o de um paciente e não tem por que chegar ao sistema.
- **Reserva com aprovação (Pedro, 28/09/2026):** a MarIA reserva
  provisoriamente e a profissional confirma ou recusa. Descartadas:
  marcar direto (a profissional perderia o filtro: alguém fora do
  perfil ou em situação de risco sairia com sessão marcada) e deixar
  configurável (fica para depois de 09/10, se fizer falta).
- **Nome e telefone no evento (Pedro, 28/09/2026):** para ligar direto
  pelo celular a partir da agenda. Ver "Segurança e LGPD".
- **Validade de 24 horas (Pedro, 28/09/2026):** sem decisão, o horário
  é liberado, para não ficar preso se ela esquecer.
- **Todos os horários livres, não um resumo (Pedro, 28/09/2026, depois
  do primeiro teste real):** a MarIA passou a ver todo início de meia em
  meia hora em que a sessão inteira cabe, em vez de 3 por dia.
- **Máximo de sessões por dia (Pedro, 28/09/2026):** campo da
  profissional; dia cheio não é oferecido.
- **Calendário no painel (Pedro, 28/09/2026):** ver a semana e marcar
  pelo painel, sem abrir o Google. O calendário mostra os títulos dos
  eventos para a profissional (é a agenda dela); a MarIA continua vendo
  só livre/ocupado.
- **Uma sessão por dia por pessoa (Pedro, 28/09/2026):** a mesma pessoa
  pode marcar em vários dias (uma sessão em cada), mas não duas no mesmo
  dia. Conta pelo contato, não pela conversa.
- **Duração da sessão no prompt (28/09/2026):** no primeiro teste pelo
  WhatsApp, a MarIA disse que não sabia quanto dura uma consulta, porque
  a duração só era usada para calcular horários. Agora vai sempre no
  prompt, valendo para "sessão", "consulta" ou "atendimento".

## Como usar

A tela tem três abas: **Calendário**, **Pedidos de horário** e
**Configurar**.

1. No menu, abra **Agenda → Configurar**.
2. Clique em **Sincronizar com o Google Agenda**. Na janela do Google,
   escolha a conta da agenda em que você marca as sessões e **deixe
   marcadas as duas permissões** (ver disponibilidade; ver e editar
   eventos). Se o navegador bloquear a janela, libere pop-ups para o
   endereço do painel.
   - Quem conectou antes, só com a disponibilidade, vê o botão
     **Permitir reservas**: ele abre a janela de novo para acrescentar a
     permissão de eventos.
3. Em **Horário de atendimento**, marque os dias em que atende e ajuste
   início e fim. Para um intervalo (ex.: almoço), use "+ Intervalo".
   Se quiser, preencha o **Máximo de sessões por dia**. Clique em
   **Salvar horário**.
4. Em **O que a MarIA vê agora**, confira os horários livres, dia a dia.
5. Na aba **Calendário**, veja a semana (‹ › troca de semana). Clique num
   espaço vazio, ou em **+ Marcar**, para marcar uma **sessão** (nome da
   pessoa; vira "Sessão · nome" no Google e conta no limite do dia) ou
   **outro compromisso** (título livre; a MarIA vê o horário como
   ocupado).
6. Quando alguém pedir um horário, ele aparece em **Pedidos de horário →
   Aguardando**, com o número no menu, e você recebe um e-mail. Clique
   em **Confirmar horário** ou **Recusar**. A pessoa recebe a resposta
   pela conversa; se a janela de 24h do WhatsApp já tiver fechado, a
   tela avisa para você falar com ela.
7. Para trocar de conta, **Trocar de conta**; para tirar o acesso,
   **Desconectar**.

A duração da sessão vem do **Perfil do atendimento**.

## Como funciona

**Conexão.** O botão usa a janela de permissão do Google (Google
Identity Services, modo popup). Ela devolve um código de uso único, que
o painel manda para `POST /calendar/{slug}/connect`. O backend troca o
código, com o segredo do cliente OAuth, por um acesso de longa duração
(`refresh_token`), confere qual conta deu a permissão e grava tudo
cifrado em `CalendarConnection`. Sem a permissão de disponibilidade, a
conexão é recusada; sem a de eventos, a MarIA só consulta. Ao
reconectar a mesma conta, se o Google não mandar um acesso novo, o
anterior continua valendo com as permissões novas.

**Horários livres** (`services/calendar.free_slots`):

- todo início de meia em meia hora (10:00, 10:30, ...) dentro do
  horário de atendimento do dia, no fuso `AGENDA_TIMEZONE`, em que a
  sessão inteira cabe no intervalo;
- no mínimo 12 horas de antecedência, nos próximos 14 dias;
- nada que encoste num período ocupado da agenda principal nem num
  pedido da MarIA ainda válido (mesmo antes de o Google refletir);
- dia que já tem `max_sessions_per_day` sessões (pedidos no prazo,
  confirmadas e as marcadas pelo painel) fica de fora.

**Na conversa.** Com a agenda pronta (conectada, com duração da sessão e
horário de atendimento), a MarIA recebe a ferramenta
`consultar_horarios_livres`, que devolve a data e a hora de agora, o
pedido que a pessoa já tiver e os horários livres, uma linha por dia
("terça, 29/09 (2026-09-29): 10:00, 10:30, ..."). O código para reservar
é a data entre parênteses, a letra T e o horário (`2026-09-29T10:00`). Com a permissão de eventos, recebe também
`pedir_agendamento(codigo, nome)`. O Google só é consultado quando ela
usa uma ferramenta.

**Reserva** (`services/appointments.request`):

1. Trava por profissional no Postgres (`pg_advisory_xact_lock`): dois
   pedidos da mesma profissional nunca são conferidos ao mesmo tempo.
2. Com a trava, confere de novo: pedidos ativos no banco e livre/ocupado
   no Google. Se o horário não está mais livre, a MarIA ouve "esse
   horário não está mais livre" e oferece outros.
3. Cria o evento "Sessão (a confirmar) · nome" (amarelo) e o
   `Appointment` provisório, válido por 24 horas.
4. Uma sessão por dia por pessoa: se ela já tem, **no mesmo dia**, um
   pedido aguardando, o horário novo substitui o anterior (o anterior é
   cancelado e o evento dele sai da agenda); se já tem sessão
   confirmada nesse dia, o pedido é recusado e a MarIA oferece outro
   dia. Pedidos e sessões em outros dias não mudam.
5. O índice único `uq_appointment_active_slot` (profissional + início,
   só para provisórios e confirmados) é a rede de segurança se algo
   escapar da trava.

A profissional recebe um e-mail ("Um horário aguarda sua confirmação")
com o dia e a hora, sem o nome da pessoa nem o conteúdo da conversa.

**Calendário do painel.** `GET /calendar/{slug}/events` lê os eventos
da semana no Google (com título) e marca quais são da MarIA (a
confirmar ou confirmados). Os títulos só vão para a tela da
profissional: não são gravados nem passam pela MarIA. `POST
/calendar/{slug}/events` marca uma sessão (evento "Sessão · nome" e um
`Appointment` confirmado com `source = "panel"`, sem conversa; recusa
se o horário já estiver ocupado) ou outro compromisso (só o evento no
Google). Precisa da permissão de eventos.

**Decisão.** Confirmar muda o evento para "Sessão · nome" (verde) e
manda à pessoa o texto fixo de confirmação. Recusar apaga o evento e
manda o texto fixo de recusa; a conversa segue com a MarIA, que pode
oferecer outros horários. No WhatsApp, o texto só sai com a janela de
24h aberta; o painel mostra se a pessoa foi avisada.

**Validade.** A cada 5 minutos (`main.py`, `EXPIRY_CHECK_SECONDS`), os
pedidos provisórios com mais de 24 horas expiram: o evento sai da agenda
e a profissional recebe um e-mail. A pessoa não é avisada (a janela do
WhatsApp quase sempre já fechou). Mesmo antes da rotina passar, um
pedido vencido não segura mais o horário e não pode ser confirmado.

Arquivos: `services/calendar.py`, `services/appointments.py`,
`routers/calendar.py`, `services/llm.py` (seção HORÁRIOS do prompt e as
ferramentas), `services/pipeline.py`, `services/notifications.py`,
`main.py` (rotina de validade), `frontend/src/pages/Agenda.jsx`,
`frontend/src/pages/agenda/WeekCalendar.jsx`, `frontend/src/google.js`.

Rotas: `GET /calendar/{slug}` (situação), `POST` e `DELETE
/calendar/{slug}/connect`, `GET /calendar/{slug}/free-slots` (prévia),
`GET /calendar/{slug}/appointments`, `POST
/calendar/appointments/{id}/approve` e `/reject`, `GET` e `POST
/calendar/{slug}/events` (calendário). O horário de atendimento e o
limite por dia são salvos pelo `PATCH /professionals/{slug}` (campos
`working_hours` e `max_sessions_per_day`).

## Textos fixos

Enviados à pessoa sem passar pelo modelo (`services/appointments.py`).
**Pendentes de aprovação da Marília.**

| Quando | Texto |
|---|---|
| Profissional confirma | "Sua sessão com {nome da profissional} está confirmada para {terça, 29/09 às 10:00}. Até lá!" |
| Profissional recusa | "{nome da profissional} não vai conseguir atender em {terça, 29/09 às 10:00}. Se quiser, posso ver outros horários com você." |

O que a MarIA diz ao reservar ("pedido registrado, a profissional
confirma") vem do modelo, guiado pelo prompt (`AGENDA_BOOKING`).

## Configuração

| Variável | Para que serve |
|---|---|
| `GOOGLE_CLIENT_ID` | O mesmo do login |
| `GOOGLE_CLIENT_SECRET` | Troca o código da janela de permissão pelo acesso à agenda. Vazio = botão desligado, com aviso na tela |
| `AGENDA_TIMEZONE` | Fuso do horário de atendimento. Padrão: `America/Sao_Paulo` |

No Google Cloud: ativar a Google Calendar API e adicionar os escopos
`calendar.freebusy` e `calendar.events` na tela de consentimento. Passo
a passo em [configuração](../tecnico/configuracao.md#3-google-agenda).

Campos da profissional: `working_hours`, `session_minutes`,
`max_sessions_per_day`.

Fixos no código: validade de 24h (`appointments.HOLD`), antecedência de
12h, horizonte de 14 dias, grade de 30 minutos
(`calendar.SLOT_STEP_MINUTES`), verificação de validade a cada 5
minutos.

## Segurança e LGPD

- **Leitura só de livre/ocupado:** título, descrição e participantes
  dos eventos da profissional não chegam ao sistema nem ao modelo.
- **Escrita só nos eventos da MarIA:** a permissão `calendar.events`
  permitiria mexer em qualquer evento; o código só cria, altera e apaga
  os eventos que ele mesmo criou (id guardado em
  `appointments.calendar_event_id`).
- **Dado do paciente no Google (decisão do Pedro, 28/09/2026):** o
  evento leva o nome que a pessoa deu e o telefone do WhatsApp. Esses
  dados passam a ficar também no Google Agenda da profissional, sob a
  conta dela, e continuam lá mesmo depois da retenção apagar a conversa
  na MarIA. Precisa constar na política de privacidade.
- No banco, o nome dado pela pessoa fica **cifrado**
  (`appointments.patient_name`); o acesso ao Google também.
- O e-mail para a profissional leva só o dia e a hora pedidos.
- **Calendário do painel:** os títulos dos eventos da profissional são
  lidos do Google só para mostrar na tela dela; não são gravados, não
  vão para logs e não passam pela MarIA.
- Desconectar revoga a permissão no Google e apaga a conexão.
- As rotas conferem se o pedido é da profissional logada (404 se não é).

## Limitações e pendências

- **Textos fixos de confirmação e recusa sem aprovação da Marília.**
- A permissão `calendar.events` é **sensível** no Google: para abrir a
  MarIA a pessoas fora dos usuários de teste, o app precisa da
  verificação do Google.
- Lê e escreve só na **agenda principal** da conta.
- A pessoa não pode desmarcar nem remarcar sozinha depois de
  confirmado; a MarIA diz que vai passar o pedido para a profissional.
- Se a profissional apagar o evento direto no Google, o pedido continua
  no painel; confirmar dá erro ("o evento não existe mais").
- Pedido expirado não avisa a pessoa.
- A rotina de validade roda dentro do backend: com o backend desligado,
  os pedidos vencidos só expiram quando ele voltar (e, enquanto isso,
  já não seguram o horário nem podem ser confirmados).
- Pedidos feitos no simulador criam eventos de verdade na agenda
  (marcados como teste na descrição).
- O limite por dia só conta as sessões que a MarIA conhece (pedidos,
  confirmadas e as marcadas pelo painel); sessões marcadas direto no
  Google não entram na conta, só ocupam o horário.
- Pelo calendário do painel ainda não dá para mover nem apagar eventos;
  isso é feito no Google Agenda.
- Com o máximo de sessões por dia, se a própria pessoa troca de horário
  num dia que ficou cheio por causa do pedido dela mesma, o novo horário
  é recusado.

## Como testar

Automático: `tests/test_calendar.py` (cálculo dos horários, horário de
atendimento, conexão, ferramenta de consulta) e
`tests/test_appointments.py` (reserva, horário ocupado, duas pessoas ao
mesmo tempo com threads de verdade, índice único, troca de horário da
mesma pessoa no mesmo dia, uma sessão por dia com vários dias
permitidos, pedido vencido, limite por dia, confirmar e recusar com e
sem janela do WhatsApp, e-mail, ferramenta só com a permissão de
eventos, sessão e compromisso marcados pelo painel, calendário da
semana).

Manual:
1. Com o `GOOGLE_CLIENT_SECRET` no `.env` e o backend reiniciado, abra
   **Agenda** e sincronize (ou **Permitir reservas**), com as duas
   permissões marcadas.
2. Preencha segunda a sexta, das 10:00 às 16:00, e salve.
3. No simulador: "quero marcar uma sessão". A MarIA oferece até 3
   horários. Escolha um e diga seu nome.
4. Confira: evento amarelo "Sessão (a confirmar) · nome" no Google
   Agenda; pedido em **Aguardando**, com o número no menu; e-mail.
5. Clique em **Confirmar horário**: o evento fica verde, e a mensagem de
   confirmação aparece na conversa (tela Conversas).
6. Repita e clique em **Recusar**: o evento sai da agenda.
7. Peça de novo o mesmo horário: ele não aparece mais (se confirmado).

## Histórico
- 28/09/2026: primeira versão (conexão pelo painel, horário de
  atendimento, horários livres na conversa, prévia na tela).
- 28/09/2026: reserva provisória pela MarIA, confirmar e recusar no
  painel, validade de 24h, e-mails, proteção contra duas pessoas no
  mesmo horário.
- 28/09/2026: todos os horários livres (grade de 30 min), máximo de
  sessões por dia, duração da sessão no prompt, calendário da semana no
  painel com marcação de sessões e compromissos, abas na tela.
- 28/09/2026: uma sessão por dia por pessoa, com várias em dias
  diferentes (antes, cada pessoa só tinha um pedido de pé).
