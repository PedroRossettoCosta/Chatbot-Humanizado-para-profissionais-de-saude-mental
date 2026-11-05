# Handoff e "Em consulta"

> Situação: funcionando no simulador e na tela de Conversas. Última atualização: 03/11/2026.

## O que é

**Handoff** é passar a conversa da SelenIA para a profissional e de
volta. Enquanto a profissional está no controle, a SelenIA fica em
silêncio naquela conversa.

**"Em consulta"** diz que a profissional está atendendo e até que
horas. Liga sozinho quando há um compromisso agora no Google Agenda, ou
pelo botão do painel. Em consulta:

- quem pedir para falar com ela fica sabendo até que horas ela atende, e
  a SelenIA oferece ajuda enquanto isso;
- a SelenIA sabe disso e responde direito a "posso falar com ela
  agora?" e "quando ela responde?";
- os e-mails de pedidos (menos pedido de horário para daqui a menos de
  12 horas, que não pode esperar) ficam guardados e chegam **num e-mail só** quando
  a consulta acaba. Alertas de segurança continuam saindo na hora.

## Por que existe

- O roteiro da demo inclui "pede humano e o bot pausa" (plano do MVP).
- A Marília decidiu em 23/09/2026 que, depois de uma emergência, o bot
  só volta quando ela liberar. Sem um botão de liberar, a conversa
  ficaria travada para sempre.
- **"Em consulta"** foi ideia do Pedro (24/09/2026): durante uma sessão
  ela não pode responder, e o lead precisa saber disso. O aviso só
  aparece quando a pessoa pede para falar com ela, não na abertura da
  conversa (decisão do Pedro, 24/09/2026).
- **"Em consulta" pela agenda, com horário, na SelenIA e nos e-mails**
  (Pedro, 03/11/2026). No teste com a Marília pelo WhatsApp, o botão
  quase não fazia diferença: ela ligou depois que as pessoas já tinham
  pedido; com ele ligado, a pessoa perguntou "a Marília tem algum
  horário disponível agora?" e a SelenIA não sabia de nada (o botão só
  mudava a mensagem fixa de um tipo de frase); e os e-mails de pedido
  chegavam no meio da sessão, quando ela não pode ler. Por isso: (1) a
  agenda liga sozinha, porque ninguém lembra de apertar o botão antes de
  cada sessão; (2) a SelenIA recebe "em atendimento até HH:MM"; (3) as
  mensagens fixas dizem o horário; (4) os e-mails de pedido viram um
  resumo no fim. Uma resposta automática nas conversas que ela assumiu
  foi proposta e **recusada pelo Pedro**: nessas conversas a SelenIA
  continua em silêncio.
- **Recusa do bot** também foi decisão do Pedro (24/09/2026): tem gente
  que não quer conversar com um bot. Nesse caso a SelenIA mostra
  compreensão, para e avisa a profissional, sem números de emergência,
  porque não é risco.

## Como usar

**Pela agenda** (com o Google Agenda conectado na tela Agenda): não
precisa fazer nada. Durante um compromisso marcado como ocupado, o topo
do painel mostra "Em consulta até HH:MM · pela agenda". Ele desliga
sozinho no fim do compromisso; **+15 min** estende pelo botão.

**Botão "Em consulta"** (na barra do topo do painel), para sessão fora
da agenda:
1. Clique em **Entrar em consulta** e escolha a duração: 50 minutos,
   1h30 ou "até eu desligar".
2. O botão vira "Em consulta até HH:MM", com **+15 min** para estender.
3. Clique em **Encerrar** para desligar antes. Com duração, ele desliga
   sozinho no horário.

**Depois da consulta**: se alguém fez um pedido enquanto você atendia,
chega um e-mail "Enquanto você atendia, N pessoas ficaram aguardando
você", com o tipo de cada pedido. As conversas estão no painel, em
"Aguardando você".

**Na conversa** (na tela [Conversas](conversas.md) ou no simulador
"Testar a SelenIA"):
- **Assumir conversa**: a SelenIA fica em silêncio.
- **Responder como {nome}**: a mensagem vai para o contato, marcada
  como sua. Responder já assume a conversa.
- **Devolver ao bot**: a SelenIA volta a responder. Também libera depois
  de uma emergência.

## Como funciona

**De onde vem o "Em consulta"** (`services/availability.py`), nesta
ordem:

1. O botão, se estiver ligado (vale primeiro: serve para sessão fora da
   agenda ou para estender).
2. A agenda: um intervalo ocupado acontecendo agora deixa a profissional
   em consulta até o fim dele. Sessões coladas contam como uma só. Bloco
   de 12 horas ou mais (evento de dia inteiro, férias) não conta.

A agenda é lida pela permissão de livre/ocupado, a mesma dos horários
livres: só horários, nunca o título do evento. A leitura fica em memória
por um minuto. Se o Google falhar, vale "fora de consulta": é melhor
avisar na hora do que segurar um aviso por engano.

**O que muda em consulta:**

| O contato diz | Fora de consulta | Em consulta |
|---|---|---|
| **Pede a profissional** ("quero falar com o Pedro", "posso falar com ela?") | Aviso de que ela foi chamada; bot para | Aviso de que ela está em atendimento **até HH:MM**; bot segue ajudando |
| **Recusa o bot** ("não quero falar com robô", "quero falar com uma pessoa") | Mensagem de compreensão; bot para; alerta | O mesmo, dizendo até que horas ela atende |
| **Qualquer outra coisa** ("ela pode me responder agora?", "quando ela volta?") | Nada muda | O prompt da SelenIA ganha a seção AGORA, com o horário de fim |

- Com o botão ligado "até eu desligar" não há horário: as mensagens e o
  prompt dizem só "responde assim que terminar".
- A seção AGORA do prompt fica no fim, depois dos trechos dos
  documentos, na parte que não entra no cache (`llm._system_blocks`):
  ela muda ao longo do dia e não pode invalidar o cache do resto.
- **E-mails em consulta** (`services/notifications.py`): o e-mail de
  pedido (falar com ela, horário especial, pagamento, valor, outro) e os
  de pedido de sessão, troca e cancelamento não saem na hora. O horário
  do pedido mais antigo fica em `held_notices_since`. A cada minuto
  (`main._held_notices_loop`), `send_held_notices` confere quem saiu de
  consulta e manda **um e-mail só** com quantas pessoas aguardam e por
  quê. Entra só o que continua pendente: se ela respondeu pelo painel
  durante a consulta, não entra; se nada ficou pendente, não sai e-mail.
  Os alertas (emergência, dúvida sobre segurança, recusa do bot) e o
  aviso de horário provisório liberado saem na hora, como sempre.

- A detecção usa **regras fixas** (`handoff.classify_request`), não o
  modelo: é previsível e barata. "Você é humana?" não conta como pedido;
  a SelenIA responde isso sozinha.
- Se a frase tiver as duas coisas ("não quero IA, quero falar com o
  Pedro"), vale a **recusa**.
- A recusa tolera erro de digitação: basta "não quero" e "robô", "bot"
  ou "máquina" a até quatro palavras de distância ("nao quero flaar co
  um robo"). "IA" fica fora dessa regra solta porque também é verbo
  ("não quero ir, ia chover").
- Também é recusa o "não" seguido de "um/uma" e robô, bot, máquina ou
  IA, mesmo sem "não quero": "quero falar com ele, não um robô ou IA".
  O artigo é o que separa isso da pergunta "você não é um robô?", que a
  SelenIA responde sozinha.
- Pedido pela profissional **não** gera alerta; gera um e-mail simples,
  uma vez, até ela responder (decisão do Pedro, 27/09/2026). A recusa do
  bot gera alerta, e o e-mail é o do alerta.
- Nos dois casos a conversa fica **"Aguardando você"**
  (`awaiting_reply_since`) até a profissional responder ou devolver a
  conversa ao bot. Até 27/09/2026 isso era a marcação "necessita
  atenção", que agora fica só para os sinais da triagem.
- **Assumir** não tira uma conversa da espera de emergência. **Devolver
  ao bot** tira, e registra `bot_released` na trilha de cada alerta
  daquela conversa.
- A triagem de segurança continua rodando com a profissional no
  controle.

Estados da conversa: `active` (SelenIA responde), `human` (profissional
no controle), `emergency_hold` (espera depois de emergência).

Arquivos: `services/handoff.py`, `routers/conversations.py`
(`/conversations/{id}`, `/take-over`, `/release`, `/messages`),
`routers/professionals.py` (`PUT`/`DELETE /professionals/{slug}/in-session`),
`routers/chat.py`, `services/availability.py` (botão ou agenda),
`services/llm.py` (seção AGORA), `services/notifications.py` (avisos
guardados e resumo), `main.py` (conferência a cada minuto),
`frontend/src/panel/InSessionControl.jsx`,
`frontend/src/panel/Simulator.jsx`.

## Textos fixos

Todos em forma neutra de gênero. **Nenhum aprovado pela Marília ainda.**

| Constante | Texto |
|---|---|
| `HANDOFF_MESSAGE` | "Claro! Vou avisar {nome}, e a resposta chega por aqui assim que possível." |
| `IN_SESSION_MESSAGE` | "{nome} está em atendimento agora e responde assim que terminar. Enquanto isso, posso te ajudar com alguma dúvida?" (botão "até eu desligar") |
| `IN_SESSION_UNTIL_MESSAGE` | "{nome} está em atendimento até as {HH:MM} e responde por aqui depois disso. Enquanto isso, posso te ajudar com alguma dúvida?" |
| `BOT_REFUSED_MESSAGE` | "Entendo, e tudo bem preferir conversar com uma pessoa. Vou parar por aqui e avisar {nome}, que responde pessoalmente por este canal assim que possível." |
| `BOT_REFUSED_IN_SESSION_MESSAGE` | "Entendo, e tudo bem preferir conversar com uma pessoa. Vou parar por aqui e avisar {nome}, que está em atendimento agora e responde pessoalmente por este canal assim que terminar." (botão "até eu desligar") |
| `BOT_REFUSED_IN_SESSION_UNTIL_MESSAGE` | "Entendo, e tudo bem preferir conversar com uma pessoa. Vou parar por aqui e avisar {nome}, que está em atendimento até as {HH:MM} e responde pessoalmente por este canal depois disso." |

E-mail de resumo (`notifications.build_held_email`), também sem
aprovação: assunto "[SelenIA] Enquanto você atendia, N pessoas ficaram
aguardando você" (ou "uma pessoa ficou"); no corpo, uma linha por tipo
de pedido ("2 pessoas: pediu para falar com você"), desde quando, o link
do painel e o lembrete de que alertas de segurança não esperam.

## Configuração

Campos da profissional: `in_session_since`, `in_session_until`
(duração entre 5 e 240 minutos, ou sem fim) e `held_notices_since`
(avisos guardados durante a consulta; nulo = nada guardado). A parte da
agenda depende do Google Agenda conectado (tela Agenda); sem ele, só o
botão vale. Nenhuma variável de ambiente nova.

## Segurança e LGPD

A mensagem da profissional é gravada cifrada, como as demais. O alerta
de recusa do bot tem nível próprio (`bot_refused`) e fica **fora** das
métricas da triagem.

Para o "Em consulta" pela agenda, a SelenIA lê só os intervalos
ocupados (permissão livre/ocupado), nunca título, descrição ou
convidados, que podem ter nome de paciente. O intervalo fica só em
memória, por um minuto. Para o contato, a SelenIA diz apenas "em
atendimento até HH:MM", nunca o que ela está fazendo.

O e-mail de resumo segue a regra dos outros: só o tipo de cada pedido e
quantas pessoas, sem nome, número ou trecho da conversa.

## Limitações e pendências

- No simulador, a resposta da profissional só é gravada; no WhatsApp,
  sai pela API da Meta ([Atendimento pelo WhatsApp](atendimento-pelo-whatsapp.md)).
- A resposta pelo painel só vale dentro da janela de 24h do WhatsApp
  (ver [Conversas](conversas.md)).
- O fim automático do "Em consulta" aparece no painel em até um
  minuto (o painel relê a profissional a cada minuto), e o resumo por
  e-mail sai em até um minuto depois do fim.
- **Qualquer compromisso ocupado conta como consulta**, inclusive um
  pessoal (dentista, almoço marcado como ocupado). Para o contato, isso
  aparece como "em atendimento até HH:MM". Para não contar, ela marca o
  evento como "livre" no Google.
- O "Em consulta" da agenda **não tem Encerrar**: se a sessão acabar
  antes, ele segue até o fim do compromisso (e o resumo espera até lá).
  Encurtar o evento no Google resolve em até um minuto.
- Nas conversas que ela assumiu, a SelenIA continua em silêncio durante
  a consulta: quem escrever ali não recebe aviso (decisão do Pedro,
  03/11/2026).
- Se ela receber pedidos em consultas seguidas sem intervalo, o resumo
  só sai no fim da última.
- As regras de detecção podem não reconhecer alguma forma de pedir,
  principalmente com erros de digitação. Frases que falharem devem virar
  caso de teste. Se isso se repetir, a alternativa é o modelo classificar
  o pedido, em vez de regras fixas.
- Os textos fixos precisam da aprovação da Marília.

## Como testar

Automático: `tests/test_handoff.py`, `tests/test_inbox.py`,
`tests/test_availability.py` (agenda, prompt, mensagens com horário,
resumo por e-mail, alerta que não espera).

Manual no simulador (conversa nova em cada caso):
1. "quero falar com o {nome}" com o botão desligado → aviso e silêncio.
2. O mesmo com "Em consulta" ligado → aviso de atendimento; o bot segue.
3. "não quero falar com robô" → compreensão, silêncio, alerta gravado.
4. Responder pela caixa verde, depois "Devolver ao bot" → a SelenIA volta.
5. Com a agenda conectada, criar no Google um evento de agora até daqui
   a 30 minutos → em até um minuto o topo mostra "Em consulta até HH:MM
   · pela agenda"; "posso falar com ela?" recebe o horário; "ela pode
   me responder agora?" também (pelo modelo).
6. Ainda em consulta, pedir para falar com ela em duas conversas → nenhum
   e-mail. Encurtar o evento para terminar agora → em até dois minutos
   chega um e-mail só, "2 pessoas ficaram aguardando você".
7. Em consulta, "to pensando em me matar" → o e-mail de emergência sai
   na hora.

## Histórico

- 24/09/2026: handoff, botão "Em consulta", recusa do bot com alerta.
- 25/09/2026: alerta de recusa do bot passa a gerar e-mail.
- 25/09/2026: recusa do bot reconhecida mesmo com erro de digitação
  (caso real do teste no simulador: "eu nao quero flaar co um robo").
- 27/09/2026: pedido de humano e recusa do bot deixam a conversa
  "Aguardando você"; pedido pela profissional passa a gerar e-mail;
  resposta pelo painel respeita a janela de 24h.
- 30/09/2026: "não um robô / não uma IA" passa a ser recusa do bot, com
  alerta (caso real do teste pelo WhatsApp: "Eu quero falar com ele não
  um robô ou ia" era tratado como simples pedido pela profissional, sem
  alerta; decisão do Pedro).
- 03/11/2026: "Em consulta" liga sozinho pela agenda; a SelenIA sabe até
  que horas ela atende (seção AGORA do prompt); mensagens fixas com o
  horário; e-mails de pedido guardados durante a consulta e enviados num
  resumo no fim. Caso real: teste com a Marília pelo WhatsApp em
  03/11/2026.
- 19/10/2026: o motivo do pedido fica em `awaiting_reason`, e a SelenIA
  ganha um quinto caminho para deixar a conversa aguardando, sem parar o
  bot: a ferramenta `avisar_profissional` (ver
  [Pedidos para a profissional](pedidos-para-a-profissional.md)).
