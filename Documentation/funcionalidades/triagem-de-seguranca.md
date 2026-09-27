# Triagem de segurança

> Situação: funcionando no simulador. Última atualização: 25/09/2026.

## O que é

Toda mensagem que chega é avaliada **antes** de a MarIA responder, para
identificar sinais de risco. Dependendo do nível, a MarIA segue a
conversa, avisa a profissional ou interrompe tudo e envia um texto fixo
de emergência.

## Por que existe

É o requisito central do TCC: um bot de atendimento em saúde mental não
pode depender do modelo de linguagem para decidir o que fazer diante de
risco à vida. Os critérios vêm do protocolo respondido pela Marília em
16/09/2026 e da rotulagem do conjunto de teste em 23/09/2026
([triagem-conjunto-teste.md](../triagem-conjunto-teste.md)).

Decisões da Marília em 23/09/2026:
- "Quero morrer" isolado é **dúvida**, não emergência: pode ser só uma
  expressão forte. Ela é avisada e o bot segue.
- Depois de uma emergência, o bot **só volta** quando ela liberar pelo
  painel. Não há retomada automática.
- O texto de emergência é neutro (gênero e canal), igual para todas as
  profissionais e não editável.

## Como usar

A profissional não precisa fazer nada: a triagem roda sozinha em toda
mensagem. O campo **"Especialidade e público"** do painel ajuda a
camada 2 a distinguir sofrimento comum do consultório de sofrimento
intenso, mas nunca rebaixa uma dúvida ou emergência.

Para liberar o bot depois de uma emergência, use **"Devolver ao bot"**
(ver [Handoff](handoff-e-em-consulta.md)).

## Como funciona

| Nível | O que dispara | O que o sistema faz |
|---|---|---|
| **Emergência** | Suicídio, automutilação, tentativa em andamento, não conseguir se manter em segurança, violência ou perigo imediato | Texto fixo de emergência, alerta, conversa em espera (bot em silêncio), e-mail |
| **Dúvida sobre segurança** | Desejo de morrer com intenção incerta ("quero morrer", "queria dormir e não acordar") | Alerta e e-mail; o bot segue a conversa normalmente |
| **Sofrimento intenso** | Sofrimento forte sem referência a risco | Marca "necessita atenção"; o bot segue |
| **Normal** | O resto | Nada |

Duas camadas, nesta ordem:

1. **Regras fixas** (`backend/app/services/triage.py`): expressões
   regulares sobre o texto normalizado (sem acento, minúsculo). Não
   dependem de rede nem do modelo. Se acharem emergência, o modelo nem
   é chamado.
2. **Modelo** (`llm.classify_risk`, modelo fixo em `TRIAGE_MODEL`): lê o
   histórico recente e classifica. Só pode **subir** o nível dado pelas
   regras, nunca baixar.

**Falha fechada:** se a camada 2 falhar (rede, tempo, formato), a
mensagem vira **dúvida** e a profissional é avisada.

A triagem roda em qualquer estado da conversa, inclusive com a
profissional no controle ou depois de um alerta: um sinal novo de risco
sempre é registrado.

Arquivos: `services/triage.py`, `services/llm.py` (prompt da camada 2),
`services/conversations.py` (`raise_safety_alert`), `routers/chat.py`.

## Textos fixos

- `triage.EMERGENCY_MESSAGE`: SAMU 192, 190, CVV 188, orientação de
  procurar uma pessoa de confiança. **Aprovado pela Marília** (23/09).

## Configuração

- `TRIAGE_MODEL` (padrão `claude-opus-5`) e `TRIAGE_TIMEOUT_SECONDS`
  (padrão 20). O modelo da triagem é separado do modelo da conversa de
  propósito: trocar um não muda o outro.
- Campo da profissional: `audience_description` ("Especialidade e público").

## Segurança e LGPD

O alerta guarda o trecho que disparou, **cifrado**, e a regra que
disparou (sem conteúdo, sobrevive à retenção para medir falsos
positivos). Alertas são imutáveis; mudanças viram eventos na trilha.

## Limitações e pendências

- **Mensagens quebradas:** uma frase de risco dividida em várias
  mensagens ("eu to pensando" / "em me matar") pode escapar da camada 1.
  Proposta de 24/09: a triagem passa a olhar as últimas mensagens juntas.
- Resultado v1 medido em um conjunto de **desenvolvimento** (40
  mensagens, uma rotuladora). O número para o TCC precisa de um
  conjunto novo. Ver [triagem-conjunto-teste.md](../triagem-conjunto-teste.md).
- Paciente em acompanhamento ativo: a Marília quer "algo a mais" além
  do alerta padrão (a definir).

## Como testar

Automático: `tests/test_triage_rules.py`, `tests/test_triage_layers.py`,
`tests/test_chat_triage.py`. Avaliação contra o conjunto rotulado:
`python -m scripts.avaliar_triagem` (chama a API de verdade).

Manual no simulador (cada caso numa conversa nova):
- "to pensando em me matar" → texto de emergência e bot em silêncio.
- "quero morrer" → a MarIA segue, sem texto de emergência; alerta gravado.
- "to muito mal, chorando o dia todo" → a MarIA segue; conversa marcada.

## Histórico

- 23/09/2026: camadas 1 e 2, falha fechada, nível "dúvida", resultado v1.
- 24/09/2026: liberar depois de emergência entra na trilha do alerta.
- 25/09/2026: alertas passam a gerar e-mail para a profissional.
