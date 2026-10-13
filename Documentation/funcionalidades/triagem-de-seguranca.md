# Triagem de segurança

> Situação: funcionando no simulador. Última atualização: 27/09/2026.

## O que é

Toda mensagem que chega é avaliada **antes** de a SelenIA responder, para
identificar sinais de risco. Dependendo do nível, a SelenIA segue a
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
2. **Modelo** (`llm.classify_risk`, modelo fixo em `TRIAGE_MODEL`): lê
   as **últimas 3 mensagens da conversa que chegaram em até 5 minutos**
   (as da pessoa e as respostas do consultório) e classifica a última.
   Só pode **subir** o nível dado pelas regras, nunca baixar.

**Falha fechada:** se a camada 2 falhar (rede, tempo, formato), a
mensagem vira **dúvida** e a profissional é avisada.

**Mensagens quebradas** (27/09/2026, pedido do Pedro): no WhatsApp a
pessoa quebra a frase ("eu to pensando" / "em me matar"), e nenhuma
parte casa sozinha com as regras. Por isso a camada 1 também roda no
texto das **últimas 3 mensagens do contato que chegaram em até 5
minutos**, juntas, mesmo com resposta da SelenIA entre elas (hoje ela
responde cada mensagem na hora, então quase nunca há duas mensagens
seguidas sem resposta).
- Só dispara o que a mensagem nova **completou**: o que já casava sem
  ela já gerou alerta e não se repete.
- Entre os níveis, o mais grave ganha ("tomei todos os" / "remédios,
  quero morrer" é emergência, não dúvida).
- O alerta guarda as mensagens juntas ("eu to pensando / em me
  matar"), e a regra ganha o sufixo `:juntas` (na tela: "frase
  quebrada em mensagens seguidas").
- O prompt da camada 2 diz para ler as últimas mensagens da pessoa
  juntas.
- Desde 30/09/2026 a camada 2 usa a mesma janela (3 mensagens, 5
  minutos) em vez das últimas 12 mensagens da conversa. Motivo, caso
  real no teste pelo WhatsApp: uma frase de emergência testada às 17:50
  fez "gostaria de marcar uma sessão para amanhã às 15:30", às 18:15,
  virar emergência também, e a pessoa recebeu de novo o texto do SAMU. O
  modelo não via horário, então o assunto de meia hora antes parecia
  continuar. Com as 12 mensagens, a classificação deu emergência 3 de 3
  vezes; só com a janela, normal 3 de 3 (decisão do Pedro).
- A **resposta** da SelenIA segue a mesma janela para o risco (30/09/2026,
  decisão do Pedro): ela continua lendo as últimas 12 mensagens, para
  não perder o fio da conversa, mas a mensagem que gerou alerta de
  emergência ou dúvida e o texto fixo de emergência saem desse
  histórico depois de 5 minutos. Caso real: 36 minutos depois de uma
  emergência de teste, a resposta a "queria marcar minha sessão amanhã"
  ainda começava lembrando o que a pessoa tinha dito sobre se matar. A
  proteção continua na triagem, que analisa cada mensagem nova.
- Os números (3 mensagens, 5 minutos) ficam em `services/pipeline.py`
  (`FRAGMENT_MESSAGES`, `FRAGMENT_WINDOW`).

No WhatsApp há também a espera antes de responder: a SelenIA aguarda
alguns segundos, junta o que chegar e responde uma vez (a API do
WhatsApp não avisa quando a pessoa está digitando). A triagem continua
rodando em cada mensagem na hora, então a espera nunca atrasa a
mensagem de emergência; a junção acima fica como segunda proteção.
Ver [Atendimento pelo WhatsApp](atendimento-pelo-whatsapp.md).

A triagem roda em qualquer estado da conversa, inclusive com a
profissional no controle ou depois de um alerta: um sinal novo de risco
sempre é registrado.

Arquivos: `services/triage.py`, `services/llm.py` (prompt da camada 2),
`services/conversations.py` (`raise_safety_alert`, `recent_history_within`),
`services/pipeline.py` (monta o contexto de cada camada), `routers/chat.py`.

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

- **Mensagens quebradas e contexto:** partes que chegam com mais de 5
  minutos de intervalo, ou mais de 3 mensagens, não são lidas juntas por
  nenhuma das camadas. Isso vale também para o contexto que deixa uma
  frase vaga grave: um "tomei" dez minutos depois de falar em remédios é
  lido sozinho. Foi a troca aceita em 30/09/2026 para uma emergência
  antiga não contaminar mensagens comuns.
- O resultado v1 da camada 2 foi medido com o histórico longo; vale
  rodar `python -m scripts.avaliar_triagem` de novo com a janela nova.
- Resultado v1 medido em um conjunto de **desenvolvimento** (40
  mensagens, uma rotuladora). O número para o TCC precisa de um
  conjunto novo. Ver [triagem-conjunto-teste.md](../triagem-conjunto-teste.md).
- Paciente em acompanhamento ativo: a Marília quer "algo a mais" além
  do alerta padrão (a definir).

## Como testar

Automático: `tests/test_triage_rules.py`, `tests/test_triage_layers.py`,
`tests/test_chat_triage.py`, `tests/test_triage_fragments.py`. Avaliação contra o conjunto rotulado:
`python -m scripts.avaliar_triagem` (chama a API de verdade).

Manual no simulador (cada caso numa conversa nova):
- "to pensando em me matar" → texto de emergência e bot em silêncio.
- "quero morrer" → a SelenIA segue, sem texto de emergência; alerta gravado.
- "to muito mal, chorando o dia todo" → a SelenIA segue; conversa marcada.
- "eu to pensando" e depois "em me matar" → texto de emergência; o
  alerta mostra as duas mensagens juntas.
- "quero morrer" e depois "oi?" → um alerta só.

## Histórico

- 23/09/2026: camadas 1 e 2, falha fechada, nível "dúvida", resultado v1.
- 27/09/2026: mensagens quebradas: a camada 1 junta as últimas 3
  mensagens do contato em até 5 minutos.
- 27/09/2026: no WhatsApp, a triagem roda assim que a mensagem chega,
  antes da espera que junta mensagens para a resposta.
- 24/09/2026: liberar depois de emergência entra na trilha do alerta.
- 25/09/2026: alertas passam a gerar e-mail para a profissional.
- 30/09/2026: a camada 2 passa a ler só as últimas 3 mensagens da
  conversa em até 5 minutos, em vez das últimas 12.
- 30/09/2026: a resposta da SelenIA deixa de ver mensagens de risco e o
  texto de emergência com mais de 5 minutos.
