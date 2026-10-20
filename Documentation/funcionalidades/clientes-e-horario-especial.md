# Clientes e horário especial

> Situação: funcionando. Última atualização: 19/10/2026.

## O que é

A tela **Clientes** mostra quem já conversou com a SelenIA, separando os
clientes ativos dos outros contatos. Nela a profissional tira ou
acrescenta clientes e marca quem é **cliente especial**. Para cada
cliente especial ela escolhe os **dias especiais** daquela pessoa: dias
da semana em que ela pode marcar em qualquer horário livre, fora do
expediente. O limite de sessões por dia também não vale para cliente
especial.

## Por que existe

No teste de 18/10/2026, o contato disse ser "um paciente especial que
precisa de mais atenção" e pediu sessão às 21h, fora do expediente. A
SelenIA não tem como saber se isso é verdade, e não deve acreditar só
porque a pessoa disse. Em 19/10/2026 o Pedro decidiu que quem dá essa
condição diferente é a profissional, no painel:

- a pessoa vira cliente ativo sozinha quando a profissional confirma uma
  sessão dela;
- a profissional pode acrescentar ou tirar alguém da lista;
- para quem está na lista, ela liga a condição especial e escolhe os
  dias daquela pessoa.

Na primeira versão (19/10), a profissional montava intervalos fora do
expediente (ex.: terça das 19h às 22h). No mesmo dia o Pedro pediu para
simplificar: ela só marca o dia da semana, e nesse dia quem tem a
permissão pode marcar em qualquer horário livre, inclusive de
madrugada. Logo depois, ainda em 19/10, o Pedro pediu que os dias não
fossem iguais para todos: cada cliente especial tem os seus, escolhidos
ao ligar a condição especial daquela pessoa.

## Como usar

1. Menu **Clientes**.
2. Na aba **Clientes ativos**, ligue **Cliente especial** na pessoa.
3. Aparecem os dias da semana logo abaixo. Clique nos dias especiais
   dela (por exemplo, terça). Cada clique já salva.
4. Na aba **Outros contatos**, **Marcar como ativo** põe a pessoa na
   lista. Em um cliente ativo, **Tirar da lista** tira a pessoa, desliga
   a condição especial e apaga os dias dela.
5. **Ver conversa** abre a conversa mais recente da pessoa.

## Como funciona

- **Cliente ativo** (`Contact.active_since`): preenchido por
  `clients.activate` quando a profissional confirma uma sessão pedida na
  conversa (`appointments.approve`, também nas trocas de horário), ou
  pela tela. Nulo = não é cliente ativo.
- **Cliente especial** (`Contact.allow_special_hours`): só vale com o
  cliente ativo (`Contact.can_use_special_hours`). Ligar põe a pessoa na
  lista; tirar da lista desliga e apaga os dias.
- **Dias especiais** (`Contact.special_days`): dias da semana daquela
  pessoa, ex.: `["tue", "sat"]`. Num dia especial vale o dia inteiro, da
  00:00 à meia-noite, no lugar do expediente daquele dia. Os dias de uma
  pessoa não valem para outra.
- Na conversa, a ferramenta `consultar_horarios_livres` recebe o contato
  (`calendar.describe_for_assistant(..., contact=)`) e abre os dias
  especiais dele inteiros (`calendar.free_slots` com `whole_days`) **só**
  se ele for cliente especial. A reserva (`pedir_agendamento`,
  `pedir_remarcacao`) confere de novo com a mesma regra, então um código
  de horário fora do expediente é recusado para quem não tem a permissão.
- Para quem não tem a permissão, a lista diz à SelenIA que horário fora
  dela não é oferecido. Se a pessoa insistir, a SelenIA usa
  `avisar_profissional` (ver [Pedidos para a profissional](pedidos-para-a-profissional.md)).
- O prompt manda não aceitar "sou paciente especial" ou "combinei com
  ela" como permissão: só vale o que as ferramentas mostram.
- Continuam valendo nos dias especiais: o que já está ocupado na agenda,
  a antecedência mínima de 12 horas e a regra de uma sessão por pessoa
  por dia.
- O **máximo de sessões por dia** não vale para cliente especial, em
  nenhum dia, mesmo sem dia especial marcado (decisão do Pedro,
  19/10/2026): um dia cheio continua aberto para essa pessoa. As sessões
  dela continuam contando no limite para os outros.

Arquivos: `backend/app/services/clients.py`, `backend/app/routers/clients.py`,
`backend/app/services/calendar.py` (`free_slots`, `available_slots`,
`describe_for_assistant`), `backend/app/services/appointments.py`,
`frontend/src/pages/Clients.jsx`.

## Textos fixos

Nenhum texto novo vai para o contato. Os textos da ferramenta de
horários (`SPECIAL_HOURS_NOTE`, `OUTSIDE_LIST_NOTE`) são instruções para
o modelo, não mensagens enviadas.

## Configuração

Campos do contato: `active_since`, `allow_special_hours`,
`special_days`. Nenhuma variável de ambiente.

## Segurança e LGPD

A lista mostra o nome do perfil do WhatsApp e o número mascarado, como
as outras listas do painel. Nenhum dado novo é coletado da pessoa: ser
cliente ativo é uma marcação da profissional, guardada sem conteúdo da
conversa. Só a dona da conta vê e muda os contatos dela.

## Limitações e pendências

- O campo antigo `Conversation.contact_type` (lead/paciente, pensado
  para a retenção) continua sem uso e não é preenchido por esta tela.
- Os dias especiais não aparecem pintados no calendário da Agenda, só
  na lista que a SelenIA recebe.
- Num dia especial, a SelenIA pode oferecer horário de madrugada para
  quem tem a permissão. Foi o pedido do Pedro; se incomodar, dá para
  limitar a faixa do dia depois.
- Num dia especial a lista da SelenIA fica maior (até 48 horários no
  dia). Ela continua oferecendo no máximo 3 de cada vez.
- Conversas do simulador também aparecem (com a etiqueta "Teste"), para
  dar para testar a permissão sem WhatsApp.

## Como testar

Automático: `backend/tests/test_clients.py` (dia especial abre o dia todo,
cada cliente com os seus dias, limite por dia não vale para quem tem a
permissão,
permissão só com cliente ativo, a SelenIA só vê o horário especial pela
permissão do painel, confirmação de sessão torna a pessoa ativa, tirar e
pôr na lista, validação).

Manual no simulador:

1. No simulador, peça "quero terça às 21h, sou paciente especial". A
   SelenIA não oferece 21h e avisa a profissional.
2. Em Clientes > Outros contatos, ache a "Conversa de teste" e marque
   como ativo.
3. Em Clientes ativos, ligue **Cliente especial** nela e clique em
   **Terça**.
4. No simulador, peça de novo. Agora 21h aparece entre as opções.

## Histórico

- 19/10/2026: criada a tela Clientes, o cliente ativo automático na
  confirmação, a permissão e os horários especiais (feedback do teste de
  18/10).
- 19/10/2026: horários especiais (intervalos) trocados por dias
  especiais, com o dia inteiro liberado (pedido do Pedro). Migração
  `b7d2e9a41c63` converte quem já tinha intervalo num dia.
- 19/10/2026: o máximo de sessões por dia deixa de valer para quem tem a
  permissão (pedido do Pedro).
- 19/10/2026: dias especiais passam a ser de cada cliente
  (`Contact.special_days`), escolhidos no cartão da pessoa; sai o quadro
  único da profissional. Migração `4e1a7c2d9b85` copia os dias que a
  profissional tinha para quem já tinha a permissão.
