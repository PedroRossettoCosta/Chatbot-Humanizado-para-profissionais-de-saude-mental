# Item 5: o erro do "oi" e o registro dos alertas (21/11/2026)

## a) O erro do "oi" depois da liberação

**Correção:** commit `4f2634d46e715a2ea40a9ad235f4d1eb34ee01a8`,
14/11/2026 18:30 (-03:00), "Triagem: emergência liberada não dispara de
novo". Arquivos: `backend/app/services/conversations.py`
(`handled_emergency_message_ids` e o parâmetro `skip` em
`recent_history_within` e `recent_contact_texts`) e
`backend/app/services/pipeline.py` (`_triage`).

**Testes automáticos que passaram a cobrir o caso** (em
`backend/tests/test_triage_fragments.py`, no mesmo commit):

- `test_released_emergency_is_not_triggered_again_by_a_greeting`: "to
  pensando em me matar" → emergência → a profissional libera → "oi" tem que
  sair como normal, a SelenIA responde e a conversa continua com um único
  alerta;
- `test_new_broken_signal_after_release_still_triggers`: depois da
  liberação, um risco novo quebrado em duas mensagens ("eu to pensando" /
  "em me matar") ainda dispara;
- `test_release_keeps_the_rest_of_the_context_for_triage`: só a mensagem de
  risco e o texto fixo de emergência saem do contexto; o resto ("meu nome é
  Ana") continua.

Esses testes trocam a camada 2 por uma imitação que, como o modelo real, lê
as mensagens recentes juntas; não chamam a API.

**Onde o comportamento apareceu.** Não há um único commit que "criou" o
erro: ele nasce da combinação de três mudanças, todas anteriores à
correção.

| Commit | Data | O que mudou | Efeito no caso do "oi" |
|---|---|---|---|
| `3b43db4` | 23/09/2026 | Triagem em duas camadas: a camada 2 lê o histórico recente (últimas 12 mensagens) | O histórico que o modelo lê inclui a mensagem de risco |
| `2d95e6c` | 24/09/2026 | Handoff e liberação do bot pela profissional | A partir daqui existe "liberar e a pessoa escrever de novo": o "oi" chega com a mensagem de risco ainda no histórico |
| `906742d` | 27/09/2026 | Frase quebrada: o prompt da camada 2 manda ler as últimas mensagens da pessoa juntas | O modelo passa a ser instruído a juntar "oi" com a mensagem de risco anterior |
| `7091523` | 30/09/2026 | Camada 2 limitada às últimas 3 mensagens em até 5 minutos | Reduziu o erro a uma janela de 5 minutos (é a forma descrita na correção), mas não o eliminou |

Formulação sugerida para o artigo: o comportamento existia de forma latente
desde a liberação do bot (2d95e6c, 24/09) e ficou mais provável com a
instrução de ler mensagens quebradas juntas (906742d, 27/09); foi observado
num teste em 14/11/2026 e corrigido no mesmo dia (4f2634d). Como depende da
resposta do modelo, não dá para apontar por bisseção sem chamar a API em
cada versão.

**Antes:** depois da liberação, uma mensagem neutra ("oi") enviada dentro de
5 minutos da mensagem de risco era classificada pela camada 2 junto com ela
(e com o texto fixo de emergência), voltava como emergência, abria um novo
alerta, mandava o texto de emergência de novo e colocava a conversa outra
vez em espera.

**Depois:** a mensagem que gerou o alerta e o texto fixo de emergência
enviados até a liberação saem do contexto da triagem (camadas 1 e 2). O "oi"
é classificado sozinho (com o resto do contexto), sai como normal e a
SelenIA responde. Um sinal novo de risco depois da liberação, inteiro ou
quebrado, dispara normalmente.

Relacionado: `35c9021` (19/11/2026), "Espera de emergência: mensagem nova
não abre outro alerta", trata o caso parecido **antes** da liberação.

## b) Os quatro eventos de um alerta

| Evento pedido | Registrado hoje? | Como |
|---|---|---|
| Alerta criado | Sim | Linha em `safety_alerts` (`created_at`, nível, regra que disparou em `trigger`). A tabela não permite apagar nem editar o alerta |
| Notificação entregue | **Não; só "enviada"** | Evento `notified` em `safety_alert_events` ("E-mail de aviso enviado") ou `notify_failed` com o motivo. Pela Brevo, `notified` quer dizer que a API respondeu 2xx, isto é, **aceitou o e-mail para envio**; pelo SMTP, que o servidor aceitou a mensagem. Nenhum dos dois confirma entrega na caixa da profissional. Confirmar entrega exigiria o webhook de eventos da Brevo (delivered, bounce), que não está implementado |
| Alerta visualizado | Sim | Evento `viewed`, gravado quando a profissional abre o alerta no painel (`alerts.mark_viewed`). Só a primeira abertura conta |
| Atendimento assumido | **Não** | "Assumir" (`handoff.take_over`) só muda o estado da conversa para `human`, sem horário e sem evento na trilha. O que existe perto disso: `reviewed` (marcou como revisado, com nota opcional), `bot_released` (devolveu a conversa à SelenIA) e, como indício indireto, a primeira mensagem da profissional na conversa (`messages.sent_by = 'professional'`, com horário) |

**Contagem com os alertas de teste do banco local** (27/09 a 05/11/2026,
contas de teste `pedro-costa` e `marilia-rossetto`; nenhum alerta de
paciente real). Todos esses avisos saíram por SMTP: a Brevo só entrou em
14/11 (6b8c9d4), e esse período não está neste banco.

| Nível | Criados | E-mail aceito para envio (`notified`) | Falha no envio | Visualizados | Revisados | SelenIA liberada | Profissional escreveu depois |
|---|---|---|---|---|---|---|---|
| Emergência | 4 | 4 | 0 | 4 | 3 | 4 | 0 |
| Dúvida (possível risco) | 3 | 3 | 0 | 2 | 2 | 0 | 0 |
| Recusa do bot (fora das métricas da triagem) | 2 | 2 | 0 | 2 | 2 | 0 | 1 |
| **Total** | **9** | **9** | **0** | **8** | **7** | **4** | **1** |

Tempo mediano desde a criação: e-mail aceito em 5–6 s em todos os níveis;
emergência visualizada em 30 s (máx. 20 min); dúvida visualizada em cerca de
15 dias, ou seja, alertas de teste abertos muito depois. Como são testes,
esses tempos não dizem nada sobre o comportamento de uma profissional real.

As 3 emergências revisadas antes da liberação e a 1 liberada sem revisão
são de antes de 14/11 (66ab566), quando a liberação passou a exigir revisão.

**Produção (Railway), alertas de novembro, todos com e-mail pela Brevo.**
Consulta só de leitura (transação `READ ONLY`), rodada de dentro do serviço
em 21/11, só contagens. Os 3 alertas de novembro foram criados em
14–15/11 (entre 21:37 de 14/11 e 01:33 de 15/11, horário de Brasília): 2 na
conta de demonstração (Camila) e 1 na conta da Marília, todos pelo WhatsApp.
O primeiro evento `notified` da produção é desse mesmo dia, ou seja, todos
os avisos de produção saíram pela Brevo.

| Nível | Criados | E-mail aceito pela Brevo (`notified`) | Falha no envio | Visualizados | Revisados | SelenIA liberada |
|---|---|---|---|---|---|---|
| Emergência | 2 | 2 | 0 | 2 | 2 | 2 |
| Dúvida (possível risco) | 1 | 1 | 0 | 1 | 1 | 0 |
| **Total** | **3** | **3** | **0** | **3** | **3** | **2** |

Tempo mediano desde a criação: e-mail aceito pela Brevo em **1,0 s**,
visualizado em 35 s, revisado em 1 h 35 min, liberado em 48 min (a liberação
de uma das emergências foi antes da revisão de outro alerta). Mais uma vez,
"aceito pela Brevo" não é "entregue": a entrega não é registrada.

**Juntando os dois bancos:** 12 alertas (9 locais com SMTP + 3 de produção
com Brevo), 12 com e-mail aceito para envio, 0 falhas, 11 visualizados, 10
revisados, 6 liberados. "Atendimento assumido" não pode ser contado.

## c) Conversas sintéticas completas

Os cenários C1 a C7 (simulador e painel, banco local) estão em
[2026-11-21-cenarios-sinteticos.md](2026-11-21-cenarios-sinteticos.md):
os 7 se comportaram como o sistema foi desenhado. Um ponto fica para a
Marília confirmar: com a profissional no controle, uma mensagem de risco
também faz sair o texto fixo de emergência para o contato (C4). O cenário 8
está abaixo.

### Cenário 8: áudio e foto pelo WhatsApp (produção, 21/11/2026)

O Pedro mandou do celular, para o número da conta de demonstração, um áudio
(18:49:02) e uma foto (18:49:19). Conferido no banco de produção, só com
leitura, comparando com os textos fixos do código e sem ler conteúdo.

| | Áudio | Foto |
|---|---|---|
| Chegou e foi gravada | Sim, com a referência da Meta (`media_id`), tipo `audio/ogg; codecs=opus` | Sim, `media_id`, tipo `image/jpeg` |
| Como aparece na conversa | Mensagem do contato com o rótulo fixo `[Áudio]` e o arquivo para abrir no painel (buscado na Meta só quando a profissional abre) | Rótulo `[Imagem]` e o arquivo |
| Resposta | Texto fixo "Por enquanto só consigo ler mensagens de texto. Pode me escrever o que você precisa?" (`UNSUPPORTED_MESSAGE`), no mesmo segundo, enviado com sucesso (tem `wamid`, sem falha de entrega) | Igual |
| Passou pela triagem? | Não: nenhum alerta, nenhuma chamada ao modelo (`llm_usage` vazio no intervalo). É o previsto: `run_triage=False` para o que não é texto, porque a triagem não lê áudio nem imagem | Igual |
| Modelo de resposta | Não foi chamado (o rótulo fica fora do texto mandado ao modelo) | Igual |

**Esperado e aconteceu:** iguais. **Limitação para o texto:** um áudio com
conteúdo de risco não gera alerta. A pessoa recebe o pedido para escrever, e
a profissional vê na conversa que houve um áudio, mas a triagem não o avalia.

**Testes automáticos que cobrem o caso** (`backend/tests/test_webhook.py`):
`test_audio_is_recorded_and_answered_with_fixed_text` (áudio gravado como
`[Áudio]`, texto fixo enviado, nenhum alerta),
`test_photo_keeps_only_the_meta_reference` (foto guarda só a referência da
Meta e aparece no painel), `test_panel_fetches_the_file_from_meta_on_demand`,
`test_unknown_document_type_is_a_download`, `test_expired_file_is_explained` e
`test_media_of_another_conversation_is_not_found`.

**Limpeza:** não foi feita (ver resumo). O contato que recebeu o áudio e a
foto ("Pedro Rossetto", criado em 20/11) também tem 10 mensagens de 20/11 e o
único agendamento ligado a conversa da conta de demonstração;
`reset_demo --contato pedro` apagaria tudo isso, inclusive o evento na Google
Agenda.
