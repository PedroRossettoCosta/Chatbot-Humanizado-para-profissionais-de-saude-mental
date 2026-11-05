# Painel

> Situação: funcionando (estrutura, Conversas, Alertas, Agenda, Perfil do atendimento, Base de conhecimento e simulador); WhatsApp em construção. Última atualização: 28/09/2026.

## O que é

Onde a profissional configura a SelenIA e acompanha o atendimento, depois
do login e do cadastro. Tem um menu lateral, uma barra no topo com o
botão "Em consulta" e o simulador "Testar a SelenIA", que abre por cima
de qualquer tela.

## Por que existe

O painel provisório (uma página só, carregada pelo slug) foi trocado
pelo visual do protótipo do Stitch (`Documentation/TCC App Design/`),
que o Pedro aprovou em 27/09/2026. As telas que só mudam de visual
vieram primeiro, para ele testar antes das que dependem de backend novo
(decisão de 27/09/2026).

## Como usar

- **Menu lateral:** Conversas, Alertas (com o número de alertas sem
  revisar), Agenda, Perfil do atendimento, WhatsApp, Base de
  conhecimento e Testar o chat. A [Agenda](agenda.md) abre desde
  28/09/2026; o [WhatsApp](conectar-whatsapp.md), desde 13/10/2026.
- **Alertas** (`/alertas`): ver [Alertas](alertas.md).
- **Conversas** (`/conversas`, onde o painel abre): ver
  [Conversas](conversas.md).
- **Barra do topo:** o botão **Entrar em consulta** (50 minutos, 1h30
  ou até desligar). Ligado, mostra "Em consulta até HH:MM", **+15 min**
  e **Encerrar**. Com o Google Agenda conectado, liga sozinho durante um
  compromisso e mostra "Em consulta até HH:MM · pela agenda", sem
  **Encerrar** (desde 03/11/2026; ver
  [Handoff e "Em consulta"](handoff-e-em-consulta.md)). Ao lado, o nome, o e-mail e **Sair**.
- **Perfil do atendimento** (`/perfil`): os mesmos campos do cadastro
  numa página, com um índice à esquerda. Nada é gravado até **Salvar
  alterações**, na barra que aparece embaixo quando há mudança; **Descartar**
  volta ao que está salvo. As regras fixas ficam recolhidas, com a data
  do aceite, em "Ver regras".
- **Base de conhecimento** (`/base-de-conhecimento`): ver
  [Base de conhecimento](base-de-conhecimento.md).
- **Testar a SelenIA** (menu, "Simular fluxo" ou o botão nas telas): um
  painel à direita com uma conversa de teste. Embaixo de cada resposta,
  etiquetas mostram o que aconteceu: nível da triagem, alerta criado,
  pedido para falar com a profissional, SelenIA pausada e os documentos
  usados. Na conversa de teste também dá para **assumir**, **responder
  como a profissional** e **devolver para a SelenIA** (ou liberar depois
  de uma emergência). Fechar o painel não apaga a conversa; "Nova
  conversa" começa outra.

No celular, o menu vira um botão no topo.

## Como funciona

- Rotas com `react-router`: `/conversas` (e `/conversas/{id}` com a
  conversa aberta), `/alertas` (e `/alertas/{id}`), `/perfil` e
  `/base-de-conhecimento`; qualquer outro
  endereço abre Conversas.
- `PanelLayout` guarda a profissional logada e a entrega às telas por
  contexto (`usePanel`); quando uma tela salva, o topo se atualiza.
  A cada minuto a profissional é relida, para o "Em consulta" que
  desliga sozinho não ficar aparecendo.
- O simulador chama `POST /chat/simulate`, o mesmo caminho do
  WhatsApp. A resposta traz `triage_level`, `alert_created` e `handoff`
  para as etiquetas. Os alertas e e-mails de teste são reais: vão para
  o e-mail de alertas cadastrado.
- "+15 min" liga de novo o "Em consulta" com o que falta mais 15
  minutos (teto de 4 horas).

Arquivos: `frontend/src/panel/` (`PanelLayout.jsx`, `InSessionControl.jsx`,
`Simulator.jsx`, `PanelContext.jsx`), `frontend/src/pages/Profile.jsx`,
`frontend/src/pages/KnowledgeBase.jsx`, `frontend/src/components/icons.jsx`,
`routers/chat.py`.

## Textos fixos

Nenhum texto novo vai para o contato. Os textos do painel seguem a
linguagem neutra de gênero (regra no `CLAUDE.md`).

## Configuração

Não se aplica.

## Segurança e LGPD

Todas as telas exigem login e mostram só os dados da profissional
logada. O simulador grava conversas de teste como qualquer conversa
(canal `simulator`), com o conteúdo cifrado e a mesma retenção.

## Limitações e pendências

- WhatsApp (05/10) ainda não existe. Na Agenda, falta a aprovação de
  horários (06/10).
- O menu no celular é o mesmo do computador, dentro de uma gaveta.
  Conversas e Alertas têm as telas de celular do protótipo (M1 a M5).

## Como testar

Automático: `test_chat_triage.py` (etiquetas da triagem na resposta do
simulador), `test_documents_api.py` (remoção de documento).

Manual:
1. Entre, abra **Perfil do atendimento**, mude o tom de voz: a barra
   "Você tem alterações não salvas" aparece; **Descartar** volta,
   **Salvar alterações** grava.
2. Ligue **Entrar em consulta → 50 minutos**, use **+15 min** e
   **Encerrar**.
3. Abra **Testar o chat**, mande "oi", depois "quero falar com você" e
   "to pensando em me matar": confira as etiquetas de cada resposta.
   Feche e abra de novo: a conversa continua lá.

## Histórico
- 27/09/2026: estrutura do painel no visual do protótipo, Perfil do
  atendimento, Base de conhecimento e simulador em painel lateral; o
  painel provisório (`Dashboard.jsx`) saiu.
- 27/09/2026: Conversas no menu; o painel passa a abrir nela.
- 27/09/2026: Alertas no menu, com o número de alertas sem revisar.
- 28/09/2026: Agenda sai do "Em breve" e abre a tela nova ([agenda](agenda.md)).
- 13/10/2026: WhatsApp sai do "Em breve" e abre a tela de conectar o número ([conectar o WhatsApp](conectar-whatsapp.md)).
