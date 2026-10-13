# Limites por contato

> Situação: funcionando; texto fixo sem aprovação. Última atualização: 12/10/2026.

## O que é
Duas travas para uma única pessoa não atrapalhar o atendimento:

- **Pedidos de horário:** cada pessoa pode ter no máximo **4 pedidos
  aguardando confirmação** ao mesmo tempo.
- **Mensagens por hora:** acima de **50 mensagens na última hora**, a
  SelenIA para de responder àquela pessoa, avisa uma vez e marca a conversa
  para você. A triagem por regras continua em toda mensagem.

As duas contam **por pessoa**, nunca pelo consultório inteiro: se
muita gente escrever ao mesmo tempo, ninguém é travado.

## Por que existe
- **Feedback da apresentação de 30/09/2026** (orientador e professora):
  pensar no que pode ser perigoso e na proteção contra abuso e prompt
  injection. Ao revisar o código em 12/10, apareceram duas brechas:
  1. A regra de uma sessão por dia deixava a mesma pessoa pedir um
     horário em cada dia, sem teto. Cada pedido segura o horário por
     24h, então alguém (um ataque, um parceiro com o celular da pessoa,
     ou só indecisão) podia travar a agenda até a profissional recusar
     um por um.
  2. Cada mensagem chama dois modelos pagos (triagem e resposta).
     Alguém mandando centenas de mensagens gerava custo sem limite.
- **Números (Pedro, 12/10/2026):** 4 pedidos pendentes e 50 mensagens
  por hora, por pessoa. A primeira proposta foi 2 e 30; o Pedro pediu
  mais folga e deixou claro que o limite não pode ser da conta inteira.
- Era item do plano de 09/10 ("limite por contato", quarta 07) que não
  tinha sido feito.

## Como usar
Não há o que configurar no painel. Quando alguém passa do limite de
mensagens, a conversa aparece com **"Necessita atenção"** na tela
Conversas, com todas as mensagens gravadas. Você pode assumir e
responder normalmente. A SelenIA volta a responder sozinha quando a conta
da última hora cair abaixo do limite.

Do lado do contato:
- No 5º pedido de horário pendente, a SelenIA explica que já há pedidos
  aguardando a profissional e que dá para pedir mais quando eles forem
  respondidos. Trocar o horário de um dia que já tem pedido continua
  valendo, e sessões confirmadas não contam.
- Na 51ª mensagem da hora, a pessoa recebe o texto fixo abaixo. Depois,
  silêncio até a hora passar.

## Como funciona
**Pedidos pendentes** (`services/appointments.py`, `request`): antes de
reservar, conta os pedidos da pessoa em situação "aguardando
confirmação" e ainda no prazo, em qualquer conversa dela. Se já são
`MAX_PENDING_REQUESTS`, a ferramenta devolve à SelenIA um texto
explicando a recusa, sem criar evento no Google. Troca de horário no
mesmo dia não conta, porque substitui o pedido anterior. O limite
também aparece no prompt (`AGENDA_BOOKING` em `services/llm.py`) e na
nota de pedidos que a ferramenta de horários devolve (`pending_note`).

**Mensagens por hora** (`services/pipeline.py`):
1. Em `receive`, depois de gravar a mensagem, conta as mensagens da
   pessoa na última hora (`conversations.contact_messages_last_hour`,
   janela móvel, todas as conversas dela com a profissional).
2. Acima de `CONTACT_MESSAGES_PER_HOUR`, a triagem roda só a **camada 1**
   (regras, sem custo). Um sinal explícito de risco continua gerando
   alerta e, em emergência, a mensagem fixa de emergência. A camada 2
   (modelo) não é chamada.
3. Na primeira mensagem acima do limite, com a conversa ativa, sai o
   texto fixo e a conversa é marcada como "necessita atenção".
4. Em `reply`, acima do limite, nada é gerado.
5. No WhatsApp (`services/whatsapp_inbox.py`), acima do limite nenhuma
   resposta é agendada e o aviso de áudio/imagem também não sai. No
   simulador (`routers/chat.py`), a resposta é o aviso na primeira vez
   e vazia depois.

A contagem vem do banco, não da memória: vale entre reinícios do
backend e para qualquer canal.

## Textos fixos
Limite de mensagens (`pipeline.RATE_LIMIT_TEMPLATE`), **sem aprovação da
Marília**:

> Recebi muitas mensagens seguidas e vou pausar minhas respostas por um
> tempo. Suas mensagens continuam registradas para {nome}. Se for uma
> emergência, ligue para o SAMU (192) ou para o CVV (188).

Os números de emergência estão no texto porque a SelenIA vai ficar em
silêncio, e quem manda muitas mensagens seguidas pode estar em crise.

A recusa do 5º pedido não é texto fixo: é uma instrução para a SelenIA,
que responde com as palavras dela.

## Configuração

| Variável | Padrão | Para que serve |
|---|---|---|
| `MAX_PENDING_REQUESTS` | 4 | Pedidos de horário aguardando confirmação ao mesmo tempo, por pessoa |
| `CONTACT_MESSAGES_PER_HOUR` | 50 | Mensagens por pessoa na última hora antes de a SelenIA pausar |

## Segurança e LGPD
Nenhum dado novo é guardado: a contagem usa as mensagens que já estão no
banco (só a quantidade e o horário, sem ler o conteúdo). Os logs não
mudam.

## Limitações e pendências
- **Texto fixo sem aprovação da Marília.**
- Acima do limite, a camada 2 da triagem não roda: um risco dito de
  forma indireta, que só o modelo pegaria, não gera alerta. Mitigação: a
  conversa já está marcada para a profissional, com tudo gravado. Foi a
  troca escolhida entre custo e segurança; se a Marília preferir, a
  camada 2 pode continuar rodando acima do limite.
- Quem troca de número (ou usa vários) tem um limite para cada número.
- Não há teto de custo da conta inteira (decisão em aberto, 12/10).

## Como testar
Automático: `tests/test_contact_limit.py` (resposta até o limite, aviso
uma vez e silêncio sem chamar o modelo, regras pegando risco acima do
limite, outra pessoa não afetada, volta quando a hora passa) e
`tests/test_appointments.py::test_pending_requests_have_a_ceiling_per_person`.

Manual, no simulador:
1. No `.env`, ponha `CONTACT_MESSAGES_PER_HOUR=3` e reinicie o backend.
2. Mande 3 mensagens: a SelenIA responde. Na 4ª chega o aviso; na 5ª,
   nada. Na tela Conversas, a conversa está com "Necessita atenção".
3. Mande "to pensando em me matar": a mensagem de emergência sai mesmo
   assim e o alerta aparece.
4. Volte o `.env` para 50.
5. Com a agenda pronta, peça horários em 5 dias diferentes: o 5º é
   recusado com explicação.

## Histórico
- 12/10/2026: primeira versão (4 pedidos pendentes e 50 mensagens por
  hora, por pessoa).
