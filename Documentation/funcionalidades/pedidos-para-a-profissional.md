# Pedidos para a profissional

> Situação: funcionando. Última atualização: 19/10/2026.

## O que é

Quando a pessoa pede algo que só a profissional decide (um horário fora
do expediente, uma forma de pagamento que a SelenIA não conhece, um
desconto, falar com ela), a SelenIA avisa a profissional por e-mail e a
conversa fica marcada como **Aguardando você** no painel. A SelenIA
continua respondendo as outras dúvidas da pessoa enquanto isso.

## Por que existe

No teste de 18/10/2026, a SelenIA disse três vezes "vou perguntar ao
Pedro" (forma de pagamento, sessão às 3h da manhã, sessão às 21h) e uma
vez "já registrei". Nada chegava à profissional: o prompt mandava dizer
isso, mas nenhum código avisava ninguém. O pedido para falar com a
profissional só funcionava com frases fixas ("quero falar com o Pedro"),
e "manda msg pro Pedro perguntando se ele topa" passava direto.

Em 19/10/2026 o Pedro pediu um protocolo de e-mail para quando a pessoa
quer falar com a profissional. Ficou assim: a SelenIA ganhou uma
ferramenta, `avisar_profissional`, e o prompt só deixa ela prometer
"vou perguntar" junto com a ferramenta.

## Como usar

A profissional não configura nada. Quando chega o e-mail "[SelenIA] Uma
pessoa aguarda uma resposta sua":

1. Abra o painel em **Conversas**. A conversa aparece em "Aguardando
   você", com o tipo do pedido na faixa amarela.
2. Responda pela própria conversa. Ao responder, você assume a conversa
   e a marcação some.

## Como funciona

Dois caminhos deixam a conversa "Aguardando você":

1. **Frases fixas** (já existia, `handoff.classify_request`): "quero
   falar com a Marília", "não quero falar com robô". Texto fixo, bot
   parado, e-mail "Uma pessoa pediu para falar com você". Ver
   [Handoff e "Em consulta"](handoff-e-em-consulta.md).
2. **Ferramenta da SelenIA** (novo, `handoff.ask_professional`): o modelo
   chama `avisar_profissional` com um motivo: `horario_especial`,
   `pagamento`, `valor`, `falar_com_profissional` ou `outro`. A conversa
   fica aguardando, o motivo vai para `Conversation.awaiting_reason` e o
   e-mail sai em segundo plano. O bot **não** para.

Regras:

- A ferramenta está sempre disponível, com ou sem agenda conectada.
- O e-mail sai uma vez por pedido: se a conversa já estava aguardando, a
  ferramenta responde ao modelo que a profissional já foi avisada e não
  manda outro.
- Responder pela conversa ou devolver ao bot limpa a marcação e o motivo.
- O prompt diz que a SelenIA só fala com a profissional pela ferramenta,
  que não pode dizer que registrou algo que nenhuma ferramenta registrou
  e que não aceita nem recusa o pedido.
- Não serve para risco: a triagem já avisa a profissional nesses casos.

Arquivos: `backend/app/services/handoff.py` (`ask_professional`),
`backend/app/services/llm.py` (`ASK_PROFESSIONAL_TOOL` e regras do
prompt), `backend/app/services/pipeline.py` (ferramentas da resposta),
`backend/app/services/notifications.py` (`request_email_text`),
`frontend/src/pages/Conversations.jsx` (faixa com o motivo).

## Textos fixos

Nenhum texto novo vai para o contato: quem fala com a pessoa é o modelo.
O e-mail para a profissional tem texto fixo por motivo
(`ASSISTANT_REQUEST_TEXT`). Não precisa da aprovação da Marília, porque
não chega ao paciente.

## Configuração

O e-mail usa o mesmo envio do alerta (`SMTP_*`) e o `alert_email` da
profissional. Nenhuma variável nova.

## Segurança e LGPD

O e-mail leva só o tipo do pedido, a hora e o canal, nunca o que a pessoa
escreveu, como os outros e-mails da SelenIA. O motivo guardado no banco é
uma categoria fixa, não um trecho da conversa.

Em 19/10/2026 o Pedro decidiu **não** pôr no e-mail um resumo do que a
pessoa perguntou, mesmo curto e escrito pela SelenIA. O resumo poderia
levar dado sensível de saúde para fora do sistema (caixa de e-mail, sem
criptografia nossa) e o modelo não garante que nunca escreveria algo
pessoal. Para saber a pergunta, a profissional abre a conversa no painel.

## Limitações e pendências

- A SelenIA decide quando chamar a ferramenta. Se o modelo prometer sem
  chamar, nada chega à profissional. O prompt proíbe, mas isso só é
  medido no teste manual.
- Um segundo pedido, antes de a profissional responder, fica junto do
  primeiro: o motivo mostrado é o do primeiro.

## Como testar

Automático: `backend/tests/test_notifications.py` (e-mail uma vez, sem
conteúdo da conversa, bot continua, motivo no painel, responder limpa,
motivo desconhecido vira "outro", frase fixa mantém o e-mail antigo) e
`backend/tests/test_reply_prompt.py` (regras do prompt).

Manual no simulador:

1. Peça "manda msg pro Pedro perguntando se ele topa às 21h".
2. A SelenIA diz que perguntou. Em Conversas, a conversa está em
   "Aguardando você" com o motivo, e o e-mail chega.
3. Peça "e como pago?" (sem formas de pagamento no Perfil). Não chega
   outro e-mail.

## Histórico

- 19/10/2026: criada a ferramenta `avisar_profissional`, o motivo do
  pedido e o e-mail por motivo (feedback do teste de 18/10).
- 19/10/2026: decidido não incluir resumo da pergunta no e-mail (LGPD).
