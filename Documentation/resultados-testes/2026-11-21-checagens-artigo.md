# Checagens rápidas no código para o artigo (21/11/2026)

Feedback do orientador, item 5 desta rodada. Respostas tiradas do código e
dos registros, sem chamar a API e sem mudar nada no sistema.

## a) Ninguém revisa um alerta: há lembrete, prazo ou escalonamento?

**Não, em nenhum dos dois níveis.** O sistema avisa uma vez e mostra o
alerta no painel até alguém revisar. Não há lembrete, prazo nem segundo
canal.

**O que acontece hoje:**

| | Emergência | Dúvida sobre segurança |
|---|---|---|
| Aviso | Um e-mail na hora (`notifications.notify_alert`), mesmo com a profissional "em consulta" | Igual |
| Se o e-mail falhar | Registra `notify_failed` com o motivo na trilha do alerta. **Não há nova tentativa** | Igual |
| No painel | O alerta fica no topo da lista com o contador "N sem revisar" (tela Alertas); a conversa mostra o botão para revisar | Igual |
| A conversa | Fica em **espera de emergência** sem prazo: a SelenIA não responde, e só volta quando a profissional revisa e libera (desde 66ab566, 14/11). Se a pessoa escrever de novo, recebe outra vez o texto fixo de emergência, **sem alerta nem e-mail novos** (35c9021, 19/11) | A SelenIA **continua respondendo** normalmente; o alerta só espera no painel |
| Lembrete, prazo ou escalonamento | Nenhum | Nenhum |

O servidor tem duas tarefas periódicas (`app/main.py`): vencer pedidos de
horário (`_expiry_loop`) e mandar o resumo do fim da consulta
(`_held_notices_loop`). Nenhuma das duas olha alertas.

**Para o texto:** a segurança da pessoa em emergência vem do texto fixo
(SAMU 192, 190, CVV 188), que sai na hora e independe da profissional. O
alerta é informativo. Um alerta de dúvida não revisado não muda nada para
a pessoa. Lembrete ou escalonamento (segundo e-mail, outro contato) fica
como trabalho futuro.

## b) A retenção de 90 dias apaga os trechos guardados nos alertas? E a conversa que nunca fica parada?

**Apaga, sim.** O script `backend/scripts/purge_old_conversations.py`
apaga as conversas cuja **última mensagem** (`last_message_at`, atualizada
a cada mensagem em `conversations.add_message`) tem mais de
`DATA_RETENTION_DAYS` (90). Pelo `cascade` do SQLAlchemy em
`Conversation`, saem junto:

- as mensagens;
- os **alertas**, inclusive o **trecho que disparou** (`excerpt`, cifrado),
  a regra (`trigger`) e toda a trilha de eventos;
- os pedidos e as sessões de horário da conversa.

O que **fica**:

| O que fica | Por quê |
|---|---|
| Linhas de `llm_usage` | Ficam com `conversation_id` nulo; só têm números, sem texto |
| O **contato** (telefone e nome de perfil, cifrados) e a marcação de cliente | O script apaga a conversa, não o contato. Esses dados ficam por tempo indeterminado |
| Eventos no Google Agenda da profissional, com nome e telefone | Estão fora do banco |
| O e-mail de aviso | Está na caixa da profissional, mas não tem conteúdo |

**Duas ressalvas para o texto:**

1. **O script é manual.** Não está agendado em produção (`railway.json`
   só inicia o servidor). Hoje, nada é apagado sozinho.
2. **Os comentários de `app/models.py` estavam desatualizados**
   (corrigidos em 21/11/2026, só o comentário). `SafetyAlert.message_id`
   dizia que "o alerta em si permanece" quando a mensagem é apagada pela
   retenção, e `trigger` dizia que "sobrevive à retenção". Pelo script, o
   alerta inteiro é apagado com a conversa, o que impede medir falsos
   positivos depois de 90 dias. O
   [seguranca-lgpd.md](../tecnico/seguranca-lgpd.md) já estava correto
   ("apagadas, junto com mensagens e alertas"). O comportamento não mudou;
   fica para decidir se o alerta deve sobreviver sem o trecho.

**Conversa que nunca fica 90 dias parada: nunca é apagada.** Cada
contato tem uma conversa por profissional e canal, reaproveitada quando a
pessoa volta. Uma paciente que escreve pelo menos uma vez a cada 90 dias
mantém **todo** o histórico, desde a primeira mensagem, por tempo
indeterminado. Não há corte por idade da mensagem. A diferença de prazo
entre paciente e lead, pedida pela Marília, também não existe (o campo
`contact_type` existe, mas a política é a mesma para todos).

## c) A média de US$ 0,13 por conversa: de quantas conversas e com quantos turnos?

**Não consegui achar a origem do número.** "0,13" não aparece em nenhum
documento nem no histórico do git. O artigo não está no repositório.
O número sai de `scripts/custo.py`, que divide o custo da tabela
`llm_usage` pelo número de conversas. Recalculei no banco local (as
mesmas 238 chamadas de 13/10 a 05/11, sem os testes de 21/11):

| Recorte (banco local) | Conversas | Custo médio por conversa | Mensagens do contato por conversa |
|---|---|---|---|
| Tudo até 05/11 | 9 | US$ 0,229 (mediana 0,184) | média 13,6, mediana 11 (1 a 31) |
| Só WhatsApp | 5 | US$ 0,312 | média 20 |
| Só simulador | 4 | US$ 0,125 | média 5,5 |
| **Só outubro (13 a 31/10)** | **3** | **US$ 0,129** | 21, 1 e 11 mensagens (média 11) |

**O único recorte que arredonda para US$ 0,13 é o de outubro:** 3
conversas, com 20 chamadas de triagem e 26 de resposta. Se o artigo usou
`custo.py --dias 30` no fim de outubro, o número vem daí. Mas uma dessas
conversas começou em 27/09, antes de a medição existir (12/10). O custo
dela está incompleto e ela tem 21 mensagens do contato para só 8 chamadas
de triagem medidas.

**Atualização (21/11/2026):** a média por conversa sugerida abaixo foi
conferida de novo, e o custo por resposta e por mensagem foi refeito,
agrupando as chamadas da mesma resposta, em
[2026-11-21-custo-isolamento-t4.md](2026-11-21-custo-isolamento-t4.md).

**Sugestão:** no artigo, trocar por um número que dá para refazer, dizendo
de onde vem. Por exemplo: "US$ 0,23 por conversa em média (mediana
US$ 0,18), em 9 conversas de teste com média de 13,6 mensagens do contato,
13/10 a 05/11/2026, banco local". Todas essas conversas são de teste.

## d) Limite do plano gratuito da Brevo

**300 e-mails por dia**, pela central de ajuda da Brevo. O limite zera
todo dia e o que não foi usado não passa para o dia seguinte. O plano
gratuito também coloca o selo "Sent with Brevo" nos e-mails. É o mesmo
número que está em [escala-e-ameacas.md](../escala-e-ameacas.md). Fonte:
<https://help.brevo.com/hc/en-us/articles/208580669>.

Só os avisos (alertas, pedidos, resumos) usam a Brevo, e cada um vai para
a profissional, não para o contato. 300 por dia sobra para o MVP. O limite
é da conta inteira, então seria compartilhado se houvesse muitas
profissionais.

## e) Sessão de validação de 03/11: quantos dos dez cenários tinham nota de segurança?

**Quatro: os cenários 7 a 10**, todos com nota 5 em segurança. Nos
cenários 1 a 6 a segurança ficou "N/A". O registro da sessão foi
transcrito em
[2026-11-03-sessao-validacao.md](2026-11-03-sessao-validacao.md) (antes
desta data, não estava no repositório).
