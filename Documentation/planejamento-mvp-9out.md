# MarIA — Planejamento do MVP (três semanas até 9/10/2026)

> Versão ajustada. Base: o planejamento escrito com o Claude web em
> 20/09 (`Downloads/planejamento-mvp-9out.md`), revisado contra o estado
> real do repositório e as decisões do projeto, e recalibrado para a
> capacidade confirmada em 20/09: **3 a 4h por dia**. As três semanas
> fecham toda sexta, dia da conversa com o Thiago.

| Semana | Período | Fecha em | Tema |
|---|---|---|---|
| 1 | 21 a 25/09 | sexta 25/09 | Núcleo de conversa + triagem (no canal simulado) |
| 2 | 28/09 a 02/10 | sexta 02/10 | Deploy, login, WhatsApp, painel operável |
| 3 | 05 a 09/10 | sexta 09/10 | Agenda, teste com a Marília, congelar, demo |

Domingo 20/09 é o dia zero: só destravar dependências externas.

**Capacidade.** 3 a 4h por dia útil, 15 dias úteis, dá **~52h**. "Hora"
aqui é sessão de trabalho: código gerado, revisão, teste e tarefas
externas. Planejei só os dias úteis. **Sábado e domingo são reserva**:
absorvem atraso e não estão no caminho crítico. O plano fecha justo nos
dias úteis, então a reserva é a rede de segurança.

---

## 0. O que mudou em relação ao plano do Claude web, e por quê

| # | Ajuste | Motivo |
|---|---|---|
| 1 | Parte do que já existe, não do zero | Já estão prontos: backend multi-tenant, RAG com ChromaDB, resposta via Claude, aviso de IA, criptografia das mensagens, script de retenção, painel simples (tom de voz, documentos, chat de teste) |
| 2 | Triagem sobe da semana 2 para a 1 | O protocolo foi respondido em 16/09 (critérios, texto de emergência, notificação). Está desbloqueada e não depende da Meta. É o que sustenta a tese |
| 3 | Canal simulado primeiro, WhatsApp como adaptador | Tudo roda no simulador do painel mesmo se a Meta atrasar |
| 4 | Plano B da Meta corrigido | O plano dizia que o número de teste resolve a demo. Não resolve: o número dos EUA não envia para números brasileiros (`planejamento-projeto.md` §5). O plano B real é o simulador |
| 5 | Alerta para a Marília **fora do painel** | Ela pediu aviso na hora, de preferência por WhatsApp. Exige template aprovado (mensagem iniciada pela empresa) e e-mail como reserva. O template de follow-up sai da lista, o de alerta entra |
| 6 | Handoff precisa de "responder pelo painel" | Sem isso o inbox mostra a conversa, mas ela não consegue assumir |
| 7 | Sessão de teste com a Marília antes do congelamento | Ela disse que revisar os cenários é "essencial", e o RNF06 exige isso antes de qualquer uso real |
| 8 | Pauta da sessão com a Marília enxugada | O texto de emergência, o que é emergência e a notificação já foram respondidos |
| 9 | Login mínimo + service account do Google | Sem tela de consentimento, sem verificação do Google, sem token que expira em 7 dias |
| 10 | Alembic, telefone criptografado, Sentry com cuidado | Banco de produção precisa de migrations (hoje é `create_all`). O telefone é dado pessoal. Sentry captura corpo de requisição e vazaria conversa clínica |
| 11 | **Escopo recalibrado para ~52h** | PIX, job agendado de retenção e log de acesso saem do MVP e vão para as semanas 4 e 5. Deploy e login viram dias separados. Cada dia tem um bloco principal |
| 12 | **A demo é o ensaio do produto da defesa** | Ver seção 1. Pesa repetibilidade e dados sintéticos, não amplitude |
| 13 | Agenda sai antes da triagem e dos alertas na ordem de corte | Triagem, alertas e auditoria nunca cortam; a agenda é P1 |

---

## 1. Escopo congelado

**Este MVP é demonstrável e testável com a Marília. Não é lançamento.**
Paciente real só entra depois da revisão dela e do lançamento gradual e
supervisionado (`planejamento-projeto.md` §2, item 6 do roadmap).

**A demo de 09/10 é para o Thiago e é o ensaio do produto que será
mostrado na defesa (prazo 13/11).** Isso muda a prioridade:

- A demo precisa ser **repetível**: dados de demonstração fixos,
  simulador do painel funcionando sem depender da Meta, vídeo de backup.
- **Só dados sintéticos** na demo. Nenhuma conversa real de paciente.
- WhatsApp real é bônus, não requisito. A defesa não pode depender de
  Meta, rede ou número de terceiros.
- A amplitude cresce depois de 09/10 (semanas 4 e 5). O que vale mais
  nesta entrega é a tese: triagem medida, RAG, arquitetura segura.

### Entra no MVP

- **Bot:** resposta imediata; aviso de IA (texto aprovado por ela);
  apresentação da profissional; RAG; preço sem informar de cara;
  triagem emergência e sofrimento intenso; retomada após alerta;
  handoff; pré-agendamento no Google Calendar.
- **Painel (uma profissional, modelo de dados continua multi-tenant):**
  login mínimo; inbox com resposta/assumir conversa; tela de alertas
  com "marcar como revisado" e trilha de auditoria; marcação
  "necessita atenção"; aprovar/recusar pré-agendamento; base de
  conhecimento e tom de voz (já existem, ganham autenticação).
- **Transversal:** deploy com HTTPS, segurança do canal, LGPD prática.

### Candidato a corte dentro do MVP

- **Agenda.** Se a semana 2 estourar, degrada para: leitura de
  disponibilidade + evento provisório criado manualmente na demo.

### Fica para as semanas 4 e 5 (antes da defesa)

- Validação de comprovante PIX (versão fina: lê o comprovante, nunca
  aprova sozinho, ela confirma).
- Job agendado de retenção (90 dias) e registro de acesso no painel.

### Sai (trabalhos futuros no TCC)

| Item | Por quê |
|---|---|
| Instagram e TikTok | Volume baixo hoje; limitações de API. Não é falta de tempo |
| Follow-up automático | Fora da janela de 24h exige template aprovado |
| Dashboard de métricas | 10º de 12 no forms; os números da triagem saem por consulta ao banco |
| Planos, Stripe, portal LGPD, cadastro self-service, Google OAuth por profissional | Já estavam fora. O OAuth só volta com o produto multi-tenant |
| Mobile/PWA | P2 no levantamento de requisitos |

### Login

Uma conta, senha com hash forte, sessão em cookie `httpOnly` +
`SameSite=Lax`, frontend e API no mesmo domínio (proxy do Caddy), rate
limit no login. Fora: cadastro, recuperação de senha, papéis. O usuário
aponta para um `professional_id`, então nada fica fixo no código
(RNF04). É obrigatório porque a tela de alertas expõe trecho de
conversa clínica na internet.

### Agenda

Decidido em 20/09: a agenda dela é o **Google Calendar**. Usa service
account; a Marília compartilha a agenda com o e-mail da service account
com permissão de edição. A service account não convida participantes,
o que não importa para evento provisório.

Para não travar o produto multi-tenant, o modelo já guarda um
`calendar_id` por profissional e a origem da credencial fica isolada
em um único módulo. No MVP a credencial é a service account; depois,
o login com o Google de cada profissional (OAuth, token criptografado)
entra como segunda opção sem mexer na lógica de disponibilidade,
oferta de horários e aprovação. A service account continua útil como
onboarding simples (a profissional escolhe qual agenda compartilhar).

---

## 2. Dia zero e tarefas externas

| # | Tarefa | Quem | Quando | Nota |
|---|---|---|---|---|
| D7 | Marcar **3 sessões** com a Marília: A (até qua 23), B (assíncrona, envio qua 30), C (qua 07/10) | Pedro | Dom 20 | A Marília é irmã do Pedro e está disponível a qualquer hora, então a sessão A pode ser conversa curta ou áudio. O que precisa ficar fechado são as datas de B e C |
| D1 | App no Meta for Developers + **número brasileiro real** dedicado (linha sem uso da casa ou chip/eSIM novo) na Cloud API | Pedro | Dom 20 | Item mais crítico do canal. O número precisa receber SMS ou ligação e não pode estar em nenhum WhatsApp. Não usar o atual da Marília sem antes checar a coexistência da Meta |
| D2 | Iniciar a verificação do negócio na Meta | Pedro | Dom 20 | Leva dias ou semanas. Não dependa dela |
| D8 | Gerar chaves novas de produção (Anthropic, `DATA_ENCRYPTION_KEY`, token da Meta) e revogar as de dev (Anthropic e "Anular tokens" do `maria-sistema`) | Pedro | Seg 28, antes do deploy | Baixa urgência: nada foi para o Git; a exposição é o histórico de conversa. Produção usa chaves separadas das de dev |
| D3 | Token permanente (System User) | Pedro | Seg 21 | O token de 24h quebra a demo |
| D4 | Submeter o template de **alerta de segurança** para a Marília | Pedro | Seg 21 | Utility; aprovação de minutos a dias |
| D5 | Google Cloud + Calendar API + service account; Marília compartilha a agenda | Pedro | Ter 22 | |
| D6 | Domínio + VPS (Docker Compose + Caddy) | Pedro | até Qui 24 | O webhook exige HTTPS público |

**Pauta da sessão A (só o que falta):**
1. Como responder à pergunta de preço (script dela)
2. Apresentação da profissional e da abordagem, nas palavras dela
3. Tom de voz: 3 exemplos de resposta boa e 3 ruins
4. O que o bot **nunca** pode dizer
5. Aviso de IA e consentimento: ela disse que ainda não decidiu
6. Regra de retomada após emergência (proposta: silêncio por 24h ou até
   ela agir; depois volta ao normal se a nova mensagem não tiver risco;
   sempre re-triar)
7. Rotular o conjunto de teste da triagem (eu levo ~40 mensagens
   rascunhadas a partir dos 11 cenários dela)

---

## 3. Semana 1: 21 a 25/09 (~17h)

**Objetivo:** conversa completa e triagem funcionando no simulador, com
os números de acerto medidos.

| Dia | ~h | Trabalho |
|---|---|---|
| Seg 21 | 3,5 | Alembic e modelo de dados: contato (telefone criptografado + hash para busca), conversa (canal, estado, lead/paciente, necessita atenção), mensagem (direção, id externo único), alerta + eventos append-only, agendamento. Interface de canal (simulador e WhatsApp). Pedro: D3 e D4 |
| Ter 22 | 3,5 | Pipeline: idempotência, agregação de fragmentos, máquina de estados (normal, emergência em espera, humano assumiu, pausado). Triagem camada 1 (frases aprovadas + mensagem fixa aprovada). Pedro: D5 |
| Qua 23 | 4 | Triagem camada 2 (LLM: normal, sofrimento intenso, emergência; modelo fixo; saída estruturada) + **falha fechada** + ~40 mensagens de teste rascunhadas. **Sessão A** |
| Qui 24 | 3,5 | Preço, apresentação e tom (a partir da sessão A); handoff (o bot pausa quando ela assume); serviço de alerta (grava + e-mail). Pedro: D6 |
| Sex 25 | 3 | Rodar o conjunto de teste, anotar números, preparar o fechamento |
| Sáb/Dom | reserva | Prioridade se algo escorregou: pipeline e triagem |

A triagem roda sobre o texto agregado e também sobre cada fragmento
(padrões inequívocos), porque uma frase de risco pode chegar quebrada
em três mensagens.

**Para o Thiago (sem escrever capítulo novo):** levar o que já existe:
levantamento de requisitos, protocolo respondido, resultado do forms e
este plano. O grosso da redação fica para depois de 09/10.

### Fechamento de sexta 25/09

**Mostrar:** no simulador do painel, o lead manda "oi" e recebe aviso de
IA e apresentação, faz uma pergunta que cai no RAG, pergunta o preço e
pede humano (o bot pausa). Depois uma mensagem de risco: mensagem fixa
aprovada e alerta gravado.

**Reportar:** status da Meta (número, verificação, template do alerta);
o que a Marília definiu; primeiros números do conjunto de teste.

**Perguntar ao Thiago:** se ele espera número medido de acurácia da
triagem ou só a descrição do mecanismo.

**Se não bateu:** preço, tom e RAG podem escorregar para a semana 2.
Modelo de dados, pipeline e triagem não.

---

## 4. Semana 2: 28/09 a 02/10 (~18h)

**Objetivo:** o sistema no ar, protegido, com WhatsApp e um painel que a
Marília consegue operar.

| Dia | ~h | Trabalho |
|---|---|---|
| Seg 28 | 3,5 | Deploy: VPS, HTTPS (Caddy), Postgres, migrations, backup para fora da máquina. Esqueleto no ar |
| Ter 29 | 3,5 | Login mínimo, todas as rotas de gestão protegidas, checagem de dono, CORS restrito, rate limit. O `/chat/simulate` público vira o simulador autenticado do painel (hoje qualquer um gasta sua chave) |
| Qua 30 | 4 | Webhook da Meta: verificação, assinatura `X-Hub-Signature-256`, deduplicação, 200 imediato com processamento assíncrono, envio de mensagem. Alerta para a Marília por template quando aprovado. **Sessão B:** enviar resultados e transcritos da triagem para ela revisar |
| Qui 01/10 | 4 | Painel: inbox (lista, conversa, chips de estado, "necessita atenção") + responder e assumir/soltar o bot. **Checkpoint** |
| Sex 02 | 3,5 | Painel: tela de alertas (trecho, horário, canal, link, revisado, trilha) + polling de 10s. Fechamento |
| Sáb/Dom | reserva | Prioridade se a semana escorregou: inbox e alertas |

**Checkpoint de quinta 01/10:** o número da Meta saiu? A semana está no
prazo? Se não, a agenda passa para o modo degradado (seção 1).

**Para o Thiago:** decisões de arquitetura já tomadas (falha fechada,
assinatura do webhook, LGPD), em uma página.

### Fechamento de sexta 02/10

**Mostrar:** mensagem entrando (no WhatsApp real, ou no simulador se não
houver número), triagem, alerta no painel com trilha de auditoria,
notificação chegando para a Marília fora do painel, e a Marília
respondendo pelo painel.

**Reportar:** números da triagem revisados por ela, com os falsos
negativos analisados um a um.

**Perguntar ao Thiago:** se a amostra basta para o capítulo de
resultados.

**Se não bateu:** inbox simplificado (lista, conversa, responder), sem
filtros. A agenda entra degradada.

---

## 5. Semana 3: 05 a 09/10 (~16h)

**Objetivo:** fechar a agenda, testar com a Marília, congelar e ensaiar.

| Dia | ~h | Trabalho |
|---|---|---|
| Seg 05 | 3,5 | Agenda (service account): leitura de disponibilidade, evento provisório, oferta de até 3 horários na conversa |
| Ter 06 | 3,5 | Aprovar/recusar no painel. Guardrails e prompt injection testados de propósito, teto de custo, limite por contato |
| Qua 07 | 3,5 | **Sessão C:** teste supervisionado com a Marília (painel + fluxo + os 11 cenários). Teste de restauração do backup |
| Qui 08 | 3,5 | Correções da sessão C. **Congelar o código ao meio-dia.** Dados sintéticos de demo, ensaio cronometrado, **vídeo de backup** |
| Sex 09 | | Demo para o Thiago |
| Sáb/Dom 03–04 | reserva | Absorve atraso da semana 2; se sobrar, adianta a agenda |

**Para o Thiago:** metodologia de teste da triagem (cenários, falso
positivo, falso negativo) em uma página.

### Roteiro da demo (ensaie nesta ordem)

1. Lead novo manda "oi": aviso de IA + apresentação
2. Pergunta sobre a abordagem: resposta via RAG
3. "Quanto custa?": tratamento do preço
4. Escolhe horário: pré-agendamento aparece no Google Calendar
5. Outra conversa, mensagem com sinal de risco: mensagem fixa, alerta no painel e aviso para a Marília fora dele
6. Painel: alerta aberto, trecho, marcar como revisado, trilha de auditoria
7. Pessoa volta a conversar: retomada sem reativar o protocolo
8. Números do teste de triagem

### Fechamento de sexta 09/10

**Mostrar:** o roteiro acima, completo.

**Perguntar ao Thiago:** duração e formato da demo na defesa; o que ele
gostaria de ver que ainda falta.

---

## 6. Depois de 09/10 (rumo à defesa)

| Semana | Foco |
|---|---|
| 12 a 16/10 | Feedback do Thiago; PIX fino; retenção agendada e log de acesso; piloto supervisionado com a Marília, só depois da aprovação dela e do aviso de IA aprovado |
| 19 a 23/10 | Polir a demo da defesa (roteiro final, dados sintéticos, vídeo); métricas e resultados no TCC |
| 26 a 30/10 | Fechar a redação; enviar a versão completa ao Thiago (30/10) |
| 02 a 13/11 | 03/11 decisão do orientador; apresentação; 06/11 docente da banca; ensaios; 13/11 prazo final |

---

## 7. Segurança e LGPD (checklist de aceite do MVP)

- **Acesso:** login em toda rota de gestão, checagem de dono, CORS só
  do domínio, HTTPS, rate limit, sem endpoint público que gaste a chave.
- **Canal:** assinatura do webhook, deduplicação, 200 imediato,
  segredos fora do código, limite por contato.
- **Clínico:** camada determinística antes do LLM; falha fechada;
  texto de emergência fixo no código, não gerado pelo modelo; alertas
  append-only; guardrails (nunca diagnosticar, nunca aconselhar
  clinicamente, nunca confirmar horário não aprovado, nunca informar
  preço fora do fluxo); mensagem do usuário e documentos tratados como
  dado, não instrução.
- **LGPD:** mensagens criptografadas (feito); telefone criptografado
  com hash para busca; aviso de IA aprovado por ela; política de
  privacidade e termos publicados. Retenção de 90 dias existe como
  script; a versão agendada e o log de acesso vêm nas semanas 4 e 5.
  Guardar telefone para marketing exige consentimento próprio e fica
  fora. O excerto do alerta segue a retenção; a trilha (horário, nível,
  quem revisou) permanece.
- **Robustez:** logs estruturados **sem conteúdo de mensagem** (Sentry
  só com scrubbing de dados; caso contrário, fora); backup do Postgres
  com restauração testada.

Consentimento no primeiro contato é decisão jurídica e de conversão (a
maior perda de leads é abandono). O código deixa o passo de "aceite"
configurável; a Marília e o Thiago decidem se entra.

---

## 8. Riscos e plano B

| Risco | Prob. | Plano B |
|---|---|---|
| Menos horas que o planejado | média | Reserva de fim de semana; depois, agenda degradada. Triagem, alertas e auditoria não cortam |
| Sem sessão A até quarta 23 | baixa | Ela é acessível a qualquer hora; fazer por áudio ou WhatsApp com a pauta. A **triagem já está desbloqueada**; o que atrasa é tom, preço e rótulos |
| Número brasileiro da Meta não sai | média | Demo no simulador do painel, que passa pelo mesmo pipeline. O número de teste dos EUA **não** serve para o Brasil |
| Template do alerta não aprovado | média | E-mail imediato + aviso no painel |
| Semana 2 estoura | alta | Inbox simplificado; agenda degradada |
| Semana 3 estoura | média | Agenda vira evento criado manualmente na demo |
| API da Claude cai na demo | baixa | Vídeo de backup do dia 8 |

**Ordem de corte:** agenda (degradada, depois manual), real-time (já é
polling), polimento de base e tom.
**Nunca corte:** triagem, alertas com auditoria, aviso de IA, proteção
de rotas, falha fechada, assinatura do webhook.

---

## 9. Decisões

**Resolvidas em 20/09:**
1. Capacidade: 3 a 4h por dia.
2. Agenda: Google Calendar (service account), sem agenda dedicada de reserva.
3. Entrega de 09/10: demo para o Thiago, ensaio do produto da defesa.

**Resolvidas em 23/09 (Marília):**
1. Caso ambíguo (não dá para saber se é brincadeira ou forma de falar):
   alerta para a profissional e o bot continua a conversa, sem a
   mensagem de emergência. Vira um terceiro nível na camada 2.
2. Retomada após emergência: o bot só volta a falar quando a
   profissional liberar pelo painel. Não há retomada automática.
3. Texto de emergência em forma neutra (gênero e canal), igual para
   todas as profissionais e não editável por elas.
4. **Preço é informado logo na primeira resposta** (inverte o "preço sem
   informar de cara" da seção 1): valor, como funciona, convite para o
   próximo passo. Nunca condicionar o preço a a pessoa contar a história.
5. Apresentação, tom de voz (3 exemplos bons e ruins) e lista de "nunca
   dizer" entregues. A lista de "nunca dizer" foi escrita para qualquer
   profissional e vira guardrail do produto, não configuração dela.

6. A assistente se chama **MarIA** em todas as contas: é o nome do
   produto, igual para toda profissional e não configurável. Ela se
   apresenta como assistente virtual e fala da profissional em terceira
   pessoa. A secretária fictícia "Isadora" dos exemplos da Marília sai.
7. Triagem em dois níveis na camada 1: sinais explícitos de suicídio,
   automutilação, tentativa e violência são emergência; desejo de morrer
   isolado ("quero morrer") é dúvida (alerta, bot segue). Vem da
   rotulagem do conjunto de teste (`triagem-conjunto-teste.md`).

**Abertas:**
1. Número brasileiro: usar uma linha sem uso da casa (dedicada ao MVP), desde que receba SMS/ligação e esteja livre de WhatsApp. Confirmar isso na segunda.
2. Fins de semana entram como capacidade ou ficam livres?
3. Aviso de IA e consentimento: recomendação de 23/09 é aceite explícito
   antes do bot responder (triagem roda mesmo antes do aceite). Validar
   com o Thiago.
4. Paciente em acompanhamento ativo com alerta de emergência: a Marília
   quer "algo a mais" além do alerta padrão. Definir o quê.
