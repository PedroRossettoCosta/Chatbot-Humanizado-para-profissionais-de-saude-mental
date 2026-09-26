# Handoff e "Em consulta"

> Situação: funcionando no simulador. Última atualização: 25/09/2026.

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

**Botão "Em consulta"** (logo abaixo do nome, no painel):
1. Escolha a duração: 50 min, 1h30 ou "até eu desligar".
2. Clique em **Entrar em consulta**. O quadro fica verde e mostra até
   que horas.
3. Clique em **Encerrar** para desligar antes. Com duração, ele desliga
   sozinho no horário.

**Na conversa** (caixa "Como profissional", abaixo do chat de teste):
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
- Pedido pelo profissional **não** gera alerta nem e-mail, só a marcação
  "necessita atenção". Só a recusa do bot gera.
- Em todos os casos a conversa fica marcada "necessita atenção".
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
`routers/chat.py`, `pages/Dashboard.jsx`.

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

- **Sem login:** qualquer um que chame a API consegue assumir ou
  responder (login planejado para 29/09).
- No simulador, a resposta da profissional só é gravada. O envio pelo
  WhatsApp vem com o webhook (30/09).
- O fim automático do "Em consulta" só aparece no painel depois de
  recarregar a página.
- As regras de detecção podem não reconhecer alguma forma de pedir,
  principalmente com erros de digitação. Frases que falharem devem virar
  caso de teste. Se isso se repetir, a alternativa é o modelo classificar
  o pedido, em vez de regras fixas.
- Não há caixa de entrada: só dá para assumir a conversa aberta no
  simulador (inbox planejado para 01/10).
- Os textos fixos precisam da aprovação da Marília.

## Como testar

Automático: `tests/test_handoff.py`.

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
