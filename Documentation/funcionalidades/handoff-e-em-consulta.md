# Handoff e "Em consulta"

> Situação: funcionando no simulador e na tela de Conversas. Última atualização: 27/09/2026.

## O que é

**Handoff** é passar a conversa da MarIA para a profissional e de
volta. Enquanto a profissional está no controle, a MarIA fica em
silêncio naquela conversa.

**"Em consulta"** é um botão do painel que avisa que a profissional
está atendendo. Com ele ligado, quem pedir para falar com ela fica
sabendo que ela está em atendimento, e a MarIA oferece ajuda enquanto
isso.

## Por que existe

- O roteiro da demo inclui "pede humano e o bot pausa" (plano do MVP).
- A Marília decidiu em 23/09/2026 que, depois de uma emergência, o bot
  só volta quando ela liberar. Sem um botão de liberar, a conversa
  ficaria travada para sempre.
- **"Em consulta"** foi ideia do Pedro (24/09/2026): durante uma sessão
  ela não pode responder, e o lead precisa saber disso. O aviso só
  aparece quando a pessoa pede para falar com ela, não na abertura da
  conversa (decisão do Pedro, 24/09/2026).
- **Recusa do bot** também foi decisão do Pedro (24/09/2026): tem gente
  que não quer conversar com um bot. Nesse caso a MarIA mostra
  compreensão, para e avisa a profissional, sem números de emergência,
  porque não é risco.

## Como usar

**Botão "Em consulta"** (na barra do topo do painel):
1. Clique em **Entrar em consulta** e escolha a duração: 50 minutos,
   1h30 ou "até eu desligar".
2. O botão vira "Em consulta até HH:MM", com **+15 min** para estender.
3. Clique em **Encerrar** para desligar antes. Com duração, ele desliga
   sozinho no horário.

**Na conversa** (na tela [Conversas](conversas.md) ou no simulador
"Testar a MarIA"):
- **Assumir conversa**: a MarIA fica em silêncio.
- **Responder como {nome}**: a mensagem vai para o contato, marcada
  como sua. Responder já assume a conversa.
- **Devolver ao bot**: a MarIA volta a responder. Também libera depois
  de uma emergência.

## Como funciona

| O contato diz | "Em consulta" desligado | "Em consulta" ligado |
|---|---|---|
| **Pede a profissional** ("quero falar com o Pedro", "posso falar com ela?") | Aviso de que ela foi chamada; bot para | Aviso de que ela está em atendimento; bot segue ajudando |
| **Recusa o bot** ("não quero falar com robô", "quero falar com uma pessoa") | Mensagem de compreensão; bot para; alerta | O mesmo, dizendo que ela responde ao terminar |

- A detecção usa **regras fixas** (`handoff.classify_request`), não o
  modelo: é previsível e barata. "Você é humana?" não conta como pedido;
  a MarIA responde isso sozinha.
- Se a frase tiver as duas coisas ("não quero IA, quero falar com o
  Pedro"), vale a **recusa**.
- A recusa tolera erro de digitação: basta "não quero" e "robô", "bot"
  ou "máquina" a até quatro palavras de distância ("nao quero flaar co
  um robo"). "IA" fica fora dessa regra solta porque também é verbo
  ("não quero ir, ia chover").
- Também é recusa o "não" seguido de "um/uma" e robô, bot, máquina ou
  IA, mesmo sem "não quero": "quero falar com ele, não um robô ou IA".
  O artigo é o que separa isso da pergunta "você não é um robô?", que a
  MarIA responde sozinha.
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

Estados da conversa: `active` (MarIA responde), `human` (profissional
no controle), `emergency_hold` (espera depois de emergência).

Arquivos: `services/handoff.py`, `routers/conversations.py`
(`/conversations/{id}`, `/take-over`, `/release`, `/messages`),
`routers/professionals.py` (`PUT`/`DELETE /professionals/{slug}/in-session`),
`routers/chat.py`, `frontend/src/panel/InSessionControl.jsx`,
`frontend/src/panel/Simulator.jsx`.

## Textos fixos

Todos em forma neutra de gênero. **Nenhum aprovado pela Marília ainda.**

| Constante | Texto |
|---|---|
| `HANDOFF_MESSAGE` | "Claro! Vou avisar {nome}, e a resposta chega por aqui assim que possível." |
| `IN_SESSION_MESSAGE` | "{nome} está em atendimento agora e responde assim que terminar. Enquanto isso, posso te ajudar com alguma dúvida?" |
| `BOT_REFUSED_MESSAGE` | "Entendo, e tudo bem preferir conversar com uma pessoa. Vou parar por aqui e avisar {nome}, que responde pessoalmente por este canal assim que possível." |
| `BOT_REFUSED_IN_SESSION_MESSAGE` | "Entendo, e tudo bem preferir conversar com uma pessoa. Vou parar por aqui e avisar {nome}, que está em atendimento agora e responde pessoalmente por este canal assim que terminar." |

## Configuração

Campos da profissional: `in_session_since`, `in_session_until`
(duração entre 5 e 240 minutos, ou sem fim).

## Segurança e LGPD

A mensagem da profissional é gravada cifrada, como as demais. O alerta
de recusa do bot tem nível próprio (`bot_refused`) e fica **fora** das
métricas da triagem.

## Limitações e pendências

- No simulador, a resposta da profissional só é gravada; no WhatsApp,
  sai pela API da Meta ([Atendimento pelo WhatsApp](atendimento-pelo-whatsapp.md)).
- A resposta pelo painel só vale dentro da janela de 24h do WhatsApp
  (ver [Conversas](conversas.md)).
- O fim automático do "Em consulta" aparece no painel em até um
  minuto (o painel relê a profissional a cada minuto).
- As regras de detecção podem não reconhecer alguma forma de pedir,
  principalmente com erros de digitação. Frases que falharem devem virar
  caso de teste. Se isso se repetir, a alternativa é o modelo classificar
  o pedido, em vez de regras fixas.
- Os textos fixos precisam da aprovação da Marília.

## Como testar

Automático: `tests/test_handoff.py`, `tests/test_inbox.py`.

Manual no simulador (conversa nova em cada caso):
1. "quero falar com o {nome}" com o botão desligado → aviso e silêncio.
2. O mesmo com "Em consulta" ligado → aviso de atendimento; o bot segue.
3. "não quero falar com robô" → compreensão, silêncio, alerta gravado.
4. Responder pela caixa verde, depois "Devolver ao bot" → a MarIA volta.

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
