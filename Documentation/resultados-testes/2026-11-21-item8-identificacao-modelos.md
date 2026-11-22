# Item 8: identificação dos modelos nas rodadas de avaliação (21/11/2026)

Pedido do orientador: os identificadores de modelo **devolvidos pela API**
em cada rodada (classificador da triagem, gerador das respostas e juiz),
os parâmetros de geração e as datas, conferindo se o juiz foi mesmo o
`claude-opus-5-5`.

## Resposta curta

**Os registros das rodadas já feitas não guardam o identificador que a API
devolveu.** Nenhum script de avaliação e nenhuma tabela do banco gravava o
campo `model` da resposta da API:

- os cabeçalhos dos resultados de 13/10 ("Modelo da resposta: ...; triagem:
  ...; juiz: ...") são impressos pelo script a partir da **configuração**
  (`settings.claude_model`, `settings.triage_model` e a constante
  `MODELO_JUIZ`), ou seja, o modelo **pedido**;
- a tabela `llm_usage` também grava o nome da configuração, não o da
  resposta (`llm._note_usage` recebe `settings.*_model`);
- o resultado da triagem de 03/11 e a análise de 23/09 trazem o modelo
  escrito à mão no texto, não na saída do script.

O que dá para afirmar com os registros é o **modelo pedido** em cada rodada
(tabela abaixo), confirmado pelo git (código commitado antes de cada data)
e, para a conversa e a triagem, pelas 238 linhas de `llm_usage` gravadas
entre 13/10 e 05/11 no banco local. Para o juiz, o registro é o cabeçalho
gerado pelo próprio script em 13/10: **`claude-opus-5-5`**. A API recusa um
identificador inexistente (erro 404), então um pedido atendido com
`claude-opus-5-5` foi atendido por esse modelo; mas o identificador
devolvido pela API não ficou gravado.

## Modelos pedidos e parâmetros, por rodada

| Rodada | Data | Papel | Modelo pedido | Parâmetros |
|---|---|---|---|---|
| Triagem v1 (+ reexecução no mesmo dia) | 23/09/2026 | Classificador (camada 2) | `claude-opus-5` | `max_tokens=2048`, `output_config.effort="low"`, saída estruturada (`RiskClassification`), sem `thinking` explícito (no Opus 5 o padrão é pensamento adaptativo), sem `temperature`/`top_p` (o Opus 5 não aceita), tempo-limite `TRIAGE_TIMEOUT_SECONDS`, 1 nova tentativa |
| Prompt injection (22 casos) e respostas sensíveis (31 casos) | 13/10/2026 | Classificador | `claude-opus-5` | iguais aos de cima |
| | | Gerador das respostas | `claude-sonnet-5` | `max_tokens=1024`, sem `thinking` nem `effort` explícitos (padrão do Sonnet 5: adaptativo, esforço `high`), sem `temperature`, cache do prompt na parte fixa, ferramentas quando aplicável |
| | | Juiz | `claude-opus-5-5` | `max_tokens=4096`, `output_config.effort="medium"`, saída estruturada (veredito + motivo), sem `temperature` (o Opus 5.5 não aceita) |
| Triagem, reexecução em 3 execuções | 03/11/2026 | Classificador | `claude-opus-5` | iguais aos de 23/09 |
| Triagem só modelo (item 4) | 21/11/2026 | Classificador | `claude-opus-5` | iguais (`max_tokens=2048`, `effort="low"`, sem `thinking` nem `temperature` explícitos, conferido nas 120 chamadas); **identificador devolvido pela API: `claude-opus-5` nas 120 chamadas** ([relatório](2026-11-21-triagem-so-modelo.md)) |

Fontes: `backend/app/config.py` (`claude_model`, `triage_model`),
`backend/app/services/llm.py` (`generate_reply`, `classify_risk`),
`backend/scripts/avaliar_respostas.py` (`MODELO_JUIZ`, chamada do juiz) e
`backend/.env` (só `CLAUDE_MODEL=claude-sonnet-5`; `TRIAGE_MODEL` não é
definido, então vale o padrão `claude-opus-5`). Esses valores são os mesmos
nos commits anteriores a cada data (3b43db4 em 23/09, 4243799 em 13/10,
63f82a1 em 19/10, válido para 03/11).

## Ressalvas para o texto

- Em 13/10 o script `avaliar_respostas.py` ainda não estava commitado (entrou
  em 63f82a1, 19/10, junto com os resultados). O cabeçalho gerado naquele dia
  é o registro de que o juiz pedido era `claude-opus-5-5`; não há versão do
  script no git anterior à rodada.
- Como a coleta guardou o modelo pedido e não o devolvido, o texto deve dizer
  "modelo solicitado à API", e não "modelo registrado na resposta".
- **Para conferir pelo lado da Anthropic:** o Console (Usage, filtrado por
  dia e por modelo) mostra quais modelos foram cobrados em 23/09, 13/10 e
  03/11. Se aparecer `claude-opus-5-5` em 13/10, isso confirma o juiz com um
  registro independente do código.
- O identificador devolvido pela API passa a ser gravado no relatório do
  item 4 (21/11), o que fecha a lacuna para o classificador.
