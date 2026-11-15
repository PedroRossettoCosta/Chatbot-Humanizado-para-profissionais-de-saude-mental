# Conversas

> Situação: funcionando (as do WhatsApp chegam quando o app da Meta for publicado). Última atualização: 27/09/2026.

## O que é

A caixa de entrada do painel: todas as conversas da SelenIA com quem
procurou a profissional. Ela vê o que a SelenIA está respondendo, quem
precisa dela primeiro, e entra na conversa quando quiser: assume,
responde e devolve para a SelenIA.

## Por que existe

- O Pedro decidiu em 26/09/2026 que a profissional responde as pessoas
  **só pelo painel**: o número conectado à SelenIA sai do app do WhatsApp
  no celular. Sem esta tela, ela não teria onde ler nem responder.
  Por isso a tela também funciona no navegador do celular (telas M1 a
  M3 do protótipo).
- Visual do protótipo do Stitch (`conversas_inbox_maria`), aprovado
  pelo Pedro em 27/09/2026.
- Decisões do Pedro em 27/09/2026:
  - **"Aguardando você"** vira uma situação própria da conversa, para
    o pedido de falar com a profissional não se perder no meio das
    outras;
  - quem pede para falar com ela gera **e-mail**, sem conteúdo da
    conversa (ver [alerta por e-mail](alerta-por-email.md));
  - as conversas do simulador aparecem na lista com a etiqueta
    **Teste**, para a tela poder ser testada antes do WhatsApp.
- **Janela de 24h**: regra da Meta. A empresa só escreve livremente
  até 24h depois da última mensagem da pessoa; fora disso, só com
  modelo de mensagem aprovado e pago. O MVP não usa modelos (decisão de
  26/09/2026, junto com os alertas só por e-mail e painel), então a
  tela trava a resposta em vez de deixar a mensagem se perder.
- **Mensagens não lidas (Pedro, 15/11/2026):** o menu **Conversas**
  mostra quantas mensagens das pessoas a profissional ainda não viu,
  como o menu Alertas mostra os alertas sem revisar. Sem isso, uma
  mensagem nova numa conversa comum (que não pede atenção) passava
  despercebida.

## Como usar

**Lista** (à esquerda no computador; tela cheia no celular):
- Cada conversa mostra o nome, o número mascarado, a hora, a
  situação e o começo da última mensagem.
- Situações:

| Etiqueta | Quando | Quem responde |
|---|---|---|
| Pausada após emergência | A triagem detectou emergência | Ninguém automático; só você, até liberar |
| Aguardando você | A pessoa pediu para falar com você ou recusou a SelenIA | Depende: com "Em consulta" ligado, a SelenIA segue ajudando |
| Necessita atenção | A triagem marcou sofrimento intenso ou dúvida sobre segurança | A SelenIA |
| Você assumiu | Você assumiu ou respondeu | Só você |
| SelenIA atendendo | O normal | A SelenIA |
| Teste | Conversa do simulador | Nada vai para o WhatsApp |

- A ordem é: emergência, aguardando você, necessita atenção, depois as
  mais recentes.
- Busca pelo nome ou pelos números, e filtros por situação.
- **Não lidas:** o menu **Conversas** mostra, num número azul, quantas
  mensagens das pessoas você ainda não viu, somando todas as conversas.
  Cada conversa da lista mostra o número dela, e a hora fica em azul.
  Abrir a conversa marca tudo como lido; enquanto ela estiver aberta na
  tela, o que chega já conta como lido. Só as mensagens da pessoa
  contam, não as respostas da SelenIA.

**Conversa aberta** (à direita; no celular, tela cheia com a seta de
voltar):
- Mensagens da pessoa à esquerda. À direita, o que saiu do sistema:
  **SelenIA**, **SelenIA · mensagem fixa** (aviso de IA, emergência,
  handoff) e **Você**.
- Botões: **Assumir conversa** (a SelenIA para), **Devolver à SelenIA** e,
  depois de uma emergência, **Liberar a SelenIA**, que pede confirmação.
- Caixa de resposta: Enter envia, Shift+Enter quebra a linha. Responder
  assume a conversa. Embaixo aparece quanto tempo falta da janela de
  24h.
- Com a janela fechada, a caixa trava e explica por quê. Ela abre de
  novo quando a pessoa escrever.

## Como funciona

- `GET /conversations?professional_slug=...` devolve a lista, já
  ordenada, com a última mensagem de cada conversa (uma consulta só,
  `DISTINCT ON`). O começo da mensagem tem até 140 caracteres.
- `GET /conversations/{id}` devolve a conversa inteira, com o número
  completo e o alerta mais recente (para a faixa de emergência).
- A lista é relida a cada 10 segundos e a conversa aberta a cada 5
  (sem tempo real no MVP).
- **Não lidas** (`conversations.read_at`): `POST /conversations/{id}/read`
  grava a hora em que ela viu a conversa. A lista devolve
  `unread_count`, as mensagens do contato (`role = user`) depois dessa
  hora, contadas numa consulta só para todas as conversas. O painel
  chama a rota ao abrir a conversa, quando chega mensagem nova com ela
  aberta e quando ela volta para a aba do painel; com a aba em segundo
  plano, nada é marcado como lido. O número do menu soma a lista, relida
  a cada 10 segundos (`PanelLayout.jsx`). As conversas que já existiam
  em 15/11/2026 começaram como lidas (migração `e6b1f3a9c824`).
- **Aguardando você** (`awaiting_reply_since`): marcado por
  `handoff.handle_human_request` quando a pessoa pede a profissional ou
  recusa a SelenIA. Sai quando ela responde ou devolve a conversa.
  Antes de 27/09/2026 esses casos marcavam "necessita atenção", que
  agora fica só para os sinais da triagem.
- **E-mail**: no pedido para falar com a profissional,
  `notifications.notify_human_request` sai uma vez, em segundo plano,
  só se a conversa ainda não estava aguardando. A recusa da SelenIA já
  gera o e-mail de alerta, então não manda outro.
- **Janela de 24h**: `last_contact_message_at` guarda a última
  mensagem da pessoa. `conversations.reply_window_open` diz se ainda
  dá para responder. Fora da janela, `POST /conversations/{id}/messages`
  responde 409. O simulador segue a mesma regra, para o teste mostrar
  o que acontece no WhatsApp.
- **Número**: mascarado na lista (`+55 21 •••••-4444`), completo na
  conversa aberta. Nome: o do perfil do WhatsApp; sem ele, o número;
  no simulador, "Conversa de teste".

Arquivos: `routers/conversations.py`, `services/conversations.py`,
`services/handoff.py`, `services/notifications.py`, `routers/chat.py`,
`frontend/src/pages/Conversations.jsx`.

## Textos fixos

Nenhum texto novo vai para o contato. O e-mail de pedido
(`notifications.HUMAN_REQUEST_SUBJECT` e `HUMAN_REQUEST_TEXT`) vai
para a profissional.

## Configuração

Não se aplica. O e-mail usa a mesma conta de envio e o mesmo
`alert_email` dos alertas.

## Segurança e LGPD

- Só a dona da conversa lista ou abre; de outra profissional, 404.
- O número aparece mascarado na lista, para quem olha a tela por cima
  do ombro não ler o número inteiro. Na conversa aberta aparece
  completo: numa emergência ela pode precisar ligar para a pessoa.
- O e-mail de pedido não leva conteúdo da conversa, e a falha no envio
  vai para o log sem conteúdo.
- As conversas continuam cifradas no banco; a tela só decifra o que a
  profissional logada pede.

## Limitações e pendências

- Conversas reais do WhatsApp só chegam com o app da Meta publicado
  (ver [Atendimento pelo WhatsApp](atendimento-pelo-whatsapp.md)).
- Numa conversa do WhatsApp, a resposta sai pela API da Meta e só é
  gravada se a Meta aceitar; se recusar, a tela mostra o erro.
- Sem tempo real: uma mensagem nova leva até 5 segundos para aparecer.
- Sem retomar conversa fora das 24h (exigiria modelo de mensagem pago,
  trabalho futuro).
- Sem anexos: só texto, nos dois sentidos.
- Sem aviso de entregue ou lido para a pessoa (o "lido" é só do lado
  do painel).
- O lido é por conversa, não por aparelho: abrir no celular marca como
  lido no computador também. Abrir a conversa conta como ler, mesmo sem
  rolar até o fim.
- O e-mail de pedido não tem trilha de envio como o de alerta; a falha
  só vai para o log.

## Como testar

Automático: `tests/test_inbox.py` (ordem da lista, "Aguardando você",
e-mail uma vez só, janela de 24h, número mascarado),
`tests/test_conversations.py` (contagem de não lidas, só mensagens da
pessoa, zera ao abrir, volta a contar com mensagem nova),
`tests/test_handoff.py`, `tests/test_auth.py` (lista de outra
profissional dá 404).

Manual:
1. Em **Testar a SelenIA**, mande "oi" e "quero falar com você". Em
   Conversas, a conversa aparece com "Aguardando você", e o e-mail
   chega.
2. Responda pela tela: vira "Você assumiu". **Devolver à SelenIA** volta
   para "SelenIA atendendo".
3. Numa conversa nova, "to pensando em me matar": vai para o topo, em
   vermelho. Teste **Liberar a SelenIA**.
4. Estreite a janela até a largura de celular: lista e conversa, uma
   de cada vez.
5. Com outra conversa aberta, mande mensagens pelo simulador: o menu
   Conversas e a conversa na lista mostram o número. Abra a conversa:
   os dois zeram.

## Histórico

- 27/09/2026: tela de Conversas (computador e celular), situação
  "Aguardando você", e-mail de pedido, janela de 24h.
- 27/09/2026: resposta pelo painel enviada de verdade no WhatsApp.
- 13/10/2026: mensagem que a Meta recusou aparece com "Não entregue" ao
  lado do horário (ver [atendimento pelo WhatsApp](atendimento-pelo-whatsapp.md)).
- 19/10/2026: a faixa "Aguardando você" diz o tipo do pedido quando foi
  a SelenIA que avisou (horário fora do atendimento, pagamento, valor,
  outra dúvida); nesses casos a SelenIA continua respondendo.
- 19/10/2026: fotos aparecem no balão (clique abre maior), áudios tocam
  no próprio painel e documentos abrem ou baixam pelo nome. O arquivo é
  buscado na Meta na hora; depois de cerca de 30 dias aparece "Arquivo
  não disponível".
- 15/11/2026: mensagens não lidas, com o número no menu Conversas e em
  cada conversa da lista (`conversations.read_at`, rota
  `POST /conversations/{id}/read`).
