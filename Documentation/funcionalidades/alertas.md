# Alertas

> Situação: funcionando. Última atualização: 27/09/2026.

## O que é

A tela onde a profissional vê cada alerta da triagem (emergência,
dúvida sobre segurança) e cada vez que alguém recusou falar com a
MarIA. Para cada um: o trecho que disparou, a regra, o que a MarIA fez
na hora e tudo o que aconteceu depois, numa trilha que ninguém edita
nem apaga. Ela marca o alerta como revisado quando terminar de cuidar
dele.

## Por que existe

- A Marília pediu para saber na hora (protocolo de 16/09/2026) e para
  poder avaliar depois se o sistema classificou certo, olhando falsos
  positivos e negativos. O e-mail avisa; esta tela é onde ela confere
  e registra.
- Requisito RNF05 ([requisitos](../levantamento-requisitos-mvp.md)):
  alerta não pode ser editado nem apagado, só marcado como revisado.
  A tabela de eventos já existia desde 22/09/2026; faltava a tela.
- Visual do protótipo do Stitch (`alertas_e_auditoria_maria` e, no
  celular, M4 e M5), aprovado pelo Pedro em 27/09/2026. Ficaram de
  fora o "reenvio em 10 minutos" e o código "#AL-…", que o Stitch
  inventou, e o botão "Manter atendimento direto", que é o mesmo que
  assumir a conversa.

## Como usar

1. O número vermelho ao lado de **Alertas**, no menu, é a quantidade
   sem revisar. Ele se atualiza a cada 10 segundos.
2. Na lista, os não revisados vêm primeiro. Filtros: não revisados,
   emergência, dúvida sobre segurança, recusou a MarIA.
3. Abra um alerta para ver:
   - o trecho que disparou e a regra ("Regra fixa: ideação suicida",
     "Análise do modelo", "a análise do modelo falhou; na dúvida,
     virou alerta");
   - o contato, com o número completo, e **Abrir conversa**;
   - com a MarIA pausada por emergência, **Liberar a MarIA para
     responder** (pede confirmação);
   - a **trilha do alerta**.
4. Escreva uma anotação, se quiser, e clique em **Marcar como
   revisado**. Só dá para revisar uma vez.

No celular, a lista e o alerta aberto aparecem um de cada vez, com a
seta de voltar.

## Como funciona

A trilha junta o próprio alerta e os eventos gravados, em ordem:

| Linha | De onde vem |
|---|---|
| Alerta criado pela triagem (ou "Pedido registrado", na recusa) | O alerta, com a regra que disparou |
| O que a MarIA fez | Derivado do nível: mensagem de emergência e pausa; seguiu a conversa; ou mensagem de compreensão e parada |
| E-mail de aviso enviado / não saiu | Evento `notified` ou `notify_failed`, com o endereço ou o motivo |
| Você abriu o alerta | Evento `viewed`, só na primeira vez |
| Marcado como revisado | Evento `reviewed`, com a anotação |
| MarIA liberada para responder | Evento `bot_released` |

- A situação ("Novo" ou "Revisado") não é coluna: é derivada da trilha.
- Não existe rota para editar nem apagar alerta; um teste garante isso.
- Liberar a MarIA usa a rota da conversa (`/conversations/{id}/release`),
  que grava `bot_released` em todos os alertas da conversa.

Rotas: `GET /alerts?professional_slug=...`, `GET /alerts/{id}`,
`POST /alerts/{id}/view` (o painel chama ao abrir),
`POST /alerts/{id}/review`.

Arquivos: `services/alerts.py`, `routers/alerts.py`,
`frontend/src/pages/Alerts.jsx`, `frontend/src/panel/PanelLayout.jsx`
(número no menu).

## Textos fixos

Nenhum texto vai para o contato. Os textos da trilha ficam em
`services/alerts.py`.

## Configuração

Não se aplica.

## Segurança e LGPD

- Só a dona vê os próprios alertas; de outra profissional, 404.
- O trecho que disparou fica cifrado no banco; a tela decifra só para
  a dona.
- **A anotação da revisão fica sem cifra**, como as outras notas da
  trilha. A tela avisa para não escrever dados clínicos ali.
- Número mascarado na lista e completo no alerta aberto, como em
  Conversas.

## Limitações e pendências

- A anotação é só registro: não muda a triagem das próximas mensagens
  da pessoa.
- Sem campo estruturado de "a triagem acertou?"; por enquanto, só
  texto livre na anotação.
- O "o que a MarIA fez" é derivado do nível do alerta, não de um evento
  gravado na hora.

## Como testar

Automático: `tests/test_alerts_api.py` (ordem da lista, trilha, visto
uma vez, revisado uma vez, liberação na trilha, sem editar nem apagar),
`tests/test_auth.py` (isolamento).

Manual:
1. No simulador, "to pensando em me matar". Em até 10 s aparece o 1 em
   Alertas.
2. Abra: criado → mensagem de emergência e pausa → e-mail → você abriu.
3. **Liberar a MarIA**: a linha nova aparece na trilha.
4. Anotação e **Marcar como revisado**: o número do menu some.
5. "não quero falar com robô" numa conversa nova: alerta de recusa.

## Histórico

- 27/09/2026: tela de Alertas (computador e celular), trilha,
  visto e revisado, número no menu.
