# Item 11: tempo até a primeira resposta (21/11/2026)

**É tempo do sistema medido em conversas de teste, não tempo de espera de
paciente real.** Nenhum conteúdo de mensagem foi lido: só os horários
gravados no banco.

## O que os registros guardam

- `messages.created_at`: quando a mensagem do contato foi gravada (logo ao
  chegar) e quando a resposta foi gravada (logo depois de gerada, **antes**
  do envio à Meta);
- `llm_usage.created_at`: fim de cada chamada ao modelo, com o propósito
  (`triage` ou `reply`). Existe desde 13/10/2026.

Dá, portanto, para medir do recebimento até a resposta pronta e separar
triagem, espera e geração. **O envio à Meta não é registrado**: falta o
tempo da chamada de envio e da entrega no celular.

## Resultado com os registros (banco local, conversas de teste no WhatsApp)

Conversas do número de teste nas contas `pedro-costa` e `marilia-rossetto`,
13/10 a 05/11/2026, só respostas geradas pelo modelo (sem emergência e sem
textos fixos). **72 respostas** com todos os horários; uma resposta pode
juntar várias mensagens quebradas (6 casos), e o tempo conta desde a
primeira mensagem sem resposta.

| Parte | Mediana | P95 |
|---|---|---|
| **Total: recebimento → resposta pronta** | **10,9 s** | **18,4 s** |
| Mensagens quebradas (da 1ª à última do grupo) | 0,0 s | 4,8 s |
| Triagem (camada 1 + camada 2, `claude-opus-5`) | 2,2 s | 3,1 s |
| Espera para juntar mensagens quebradas (fixa) | 6,0 s | 6,0 s |
| Geração da resposta (RAG + `claude-sonnet-5`, com ferramentas quando houve) | 2,3 s | 8,8 s |
| Gravação | 0,01 s | 0,01 s |

- Sem ferramenta (50 respostas): mediana 10,3 s, P95 16,1 s.
- Com consulta à agenda ou outra ferramenta (22): mediana 13,7 s, P95 18,9 s.
- A espera de 6 s (`REPLY_DEBOUNCE_SECONDS`) começa depois da triagem e é
  igual para todas; a geração foi estimada como o intervalo entre o fim da
  triagem e o fim da última chamada de resposta, menos esses 6 s.
- Máximo de 92,8 s num caso isolado, que não afeta a mediana nem o P95.

**Emergências (texto fixo, sem modelo de resposta), à parte:** 4 casos, de
2,9 s a 3,5 s entre a mensagem e o texto de emergência gravado (mediana
3,1 s). Nos 3 casos depois de 13/10 a triagem pelo modelo levou 2,9–3,1 s
desse total; o de 27/09 (simulador) é de antes do registro por chamada. O
texto de emergência não espera os 6 s.

## Ressalvas

1. O ambiente é a máquina do Pedro com túnel para o webhook, não o Railway.
2. São conversas de teste no número de teste; o conteúdo não foi conferido
   aqui para dizer que todas são sintéticas.
3. O simulador ("Testar a SelenIA") tem só 6 respostas registradas no banco
   local, quase todas de antes de existir `llm_usage`; não dá para usar.
4. O pedido do orientador prefere o lote sintético na produção. Esse lote
   está pendente da aprovação do custo (ver resumo de 21/11).
