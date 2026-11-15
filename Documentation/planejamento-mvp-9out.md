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
| 5 | Alerta para a Marília **fora do painel** | Ela pediu aviso na hora. Decidido em 26/09: o aviso vai por **e-mail** (feito em 25/09) e pelo painel; no futuro, pela notificação do app. Não usa WhatsApp: mensagem iniciada pela empresa exige template e forma de pagamento na Meta |
| 6 | Handoff precisa de "responder pelo painel" | Sem isso o inbox mostra a conversa, mas ela não consegue assumir |
| 7 | Sessão de teste com a Marília antes do congelamento | Ela disse que revisar os cenários é "essencial", e o RNF06 exige isso antes de qualquer uso real |
| 8 | Pauta da sessão com a Marília enxugada | O texto de emergência, o que é emergência e a notificação já foram respondidos |
| 9 | Login mínimo + service account do Google | Sem tela de consentimento, sem verificação do Google, sem token que expira em 7 dias |
| 10 | Alembic, telefone criptografado, Sentry com cuidado | Banco de produção precisa de migrations (hoje é `create_all`). O telefone é dado pessoal. Sentry captura corpo de requisição e vazaria conversa clínica |
| 11 | **Escopo recalibrado para ~52h** | PIX, job agendado de retenção e log de acesso saem do MVP e ficam para depois de 09/10. Deploy e login viram dias separados. Cada dia tem um bloco principal |
| 12 | **A demo é o ensaio do produto da defesa** | Ver seção 1. Pesa repetibilidade e dados sintéticos, não amplitude |
| 13 | Agenda sai antes da triagem e dos alertas na ordem de corte | Triagem, alertas e auditoria nunca cortam; a agenda é P1 |
| 14 | **Login com Google, cadastro em etapas e adicionar número pelo painel entram no MVP** (26/09) | O produto parte da ideia de registrar o número de cada profissional. Sem verificação do negócio a conta da Meta aceita 2 números, o suficiente para mostrar o fluxo com um segundo chip. Para caber, a agenda entra enxuta e o guia de contêineres fica para depois de 09/10 |

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
- **O MVP fecha em 09/10** e a partir daí o foco principal é o artigo
  (decisão do Pedro, 27/09). Até 09/10 entra só o que já está planejado;
  os extras da seção "Fica para depois de 09/10" são feitos depois, em
  paralelo com a redação. O que vale mais nesta entrega é a tese:
  triagem medida, RAG, arquitetura segura.

### Entra no MVP

- **Bot:** resposta imediata; aviso de IA (texto aprovado por ela);
  apresentação da profissional; RAG; preço sem informar de cara;
  triagem emergência e sofrimento intenso; retomada após alerta;
  handoff; pré-agendamento no Google Calendar.
- **Painel (uma profissional, modelo de dados continua multi-tenant):**
  login com Google e cadastro em etapas (perfil do atendimento
  completo antes de liberar o painel); adicionar o número de WhatsApp
  da profissional pelo painel (código por SMS); inbox com
  resposta/assumir conversa; tela de alertas
  com "marcar como revisado" e trilha de auditoria; marcação
  "necessita atenção"; aprovar/recusar pré-agendamento; base de
  conhecimento e tom de voz (já existem, ganham autenticação).
- **Transversal:** deploy com HTTPS, segurança do canal, LGPD prática.

### Candidato a corte dentro do MVP

- **Agenda.** Com a entrada do login com Google, do cadastro e do
  número (26/09), já entra enxuta: leitura de disponibilidade, oferta de
  horários e evento provisório. Aprovar/recusar no painel só se couber;
  senão ela aprova no próprio Google Calendar. Se a semana 3 estourar,
  o evento é criado manualmente na demo.

### Fica para depois de 09/10 (em paralelo com o artigo)

Não entra antes de 09/10, nem se sobrar tempo (decisão de 27/09):

- Validação de comprovante PIX (versão fina: lê o comprovante, nunca
  aprova sozinho, ela confirma).
- Job agendado de retenção (90 dias) e registro de acesso no painel. A
  retenção existe como script manual.
- Cadastro com aprovação no lugar da lista de convidados, e publicação
  do app no Google.
- Contêineres e guia de deploy.
- Aprovar/recusar agendamento no painel, se não couber até 09/10 (até
  lá, ela aprova no próprio Google Calendar).

### Sai (trabalhos futuros no TCC)

| Item | Por quê |
|---|---|
| Instagram e TikTok | Volume baixo hoje; limitações de API. Não é falta de tempo |
| Follow-up automático | Fora da janela de 24h exige template aprovado |
| Dashboard de métricas | 10º de 12 no forms; os números da triagem saem por consulta ao banco |
| Planos, Stripe, portal LGPD, cadastro aberto a qualquer pessoa | Já estavam fora. O cadastro do MVP é só para e-mails autorizados |
| Conectar o número que a profissional já usa (coexistência com o app WhatsApp Business) | Exige ser Provedor de Tecnologia da Meta, com verificação do negócio (CNPJ) e revisão do app |
| Mobile/PWA | P2 no levantamento de requisitos |
| Omnichannel (Chatwoot ou similar) | Sugestão do feedback de 30/09; na defesa, só WhatsApp (12/10) |

### Login

Decidido em 26/09: **login com Google**, só para identificar a pessoa
(nome, e-mail, foto; sem acesso à agenda, que continua com a service
account). No MVP só entram **e-mails autorizados** listados no `.env`
(Pedro e Marília), para ninguém usar a MarIA e gastar a chave. Sessão
em cookie `httpOnly` + `SameSite=Lax` (`Secure` ligado por
configuração), rate limit. No primeiro acesso a profissional passa pelo
**cadastro em etapas** (dados, atendimento, tom de voz, leitura e
aceite das regras fixas, regras extras, revisão); o painel só libera
com o perfil completo. O `slug` passa a ser gerado do nome. Fora:
recuperação de senha (não há senha) e papéis. É obrigatório porque a
tela de alertas expõe trecho de conversa clínica.

### Número da profissional

Decidido em 26/09: a profissional adiciona o número pelo painel. O
sistema chama a API da Meta com o token do usuário do sistema: adiciona
o número à conta do WhatsApp Business da MarIA, pede o código por SMS,
confere o código e registra. O número fica ligado à profissional
(`whatsapp_phone_number_id`) e o webhook usa isso para rotear.

Limites: sem verificação do negócio a conta aceita **2 números** (o
chip da MarIA e o de uma profissional); o número não pode estar em
nenhum WhatsApp; excluir só pelo WhatsApp Manager, não pela API;
**10 registros por número a cada 72h** (acima disso, bloqueio de 3
dias, então os ensaios são contados). Conectar o número que a
profissional já usa no celular (coexistência) fica fora (seção
"Sai").

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

**Mudou em 28/09 (Pedro):** no lugar da service account, a profissional
conecta a agenda pelo painel (botão "Sincronizar com o Google Agenda",
janela de permissão do Google) e preenche o horário de atendimento na
tela Agenda. Permissão só de livre/ocupado; o acesso fica cifrado no
banco. Ver [agenda](funcionalidades/agenda.md).

---

## 2. Dia zero e tarefas externas

| # | Tarefa | Quem | Quando | Nota |
|---|---|---|---|---|
| D7 | Marcar **3 sessões** com a Marília: A (até qua 23), B (assíncrona, envio qua 30), C (qua 07/10) | Pedro | Dom 20 | A Marília é irmã do Pedro e está disponível a qualquer hora, então a sessão A pode ser conversa curta ou áudio. O que precisa ficar fechado são as datas de B e C |
| D1 | App no Meta for Developers + **número brasileiro real** dedicado (linha sem uso da casa ou chip/eSIM novo) na Cloud API | Pedro | Dom 20 | Item mais crítico do canal. O número precisa receber SMS ou ligação e não pode estar em nenhum WhatsApp. Não usar o atual da Marília sem antes checar a coexistência da Meta |
| D2 | Iniciar a verificação do negócio na Meta | Pedro | Dom 20 | Leva dias ou semanas. Não dependa dela |
| D8 | Gerar chaves novas de produção (Anthropic, `DATA_ENCRYPTION_KEY`, token da Meta) e revogar as de dev (Anthropic e "Anular tokens" do `maria-sistema`) | Pedro | Só quando houver deploy (ver D6) | Baixa urgência: nada foi para o Git; a exposição é o histórico de conversa. Produção usa chaves separadas das de dev |
| D3 | Token permanente (System User) | Pedro | Seg 21 | O token de 24h quebra a demo |
| D4 | ~~Submeter o template de alerta de segurança~~ | | | **Cancelado em 26/09:** o alerta vai por e-mail e painel, sem WhatsApp, então não precisa de template nem de forma de pagamento na Meta |
| D5 | Google Cloud + Calendar API + service account; Marília compartilha a agenda | Pedro | Ter 22 | |
| D9 | Criar o cliente OAuth do Google (tela de consentimento em modo de teste, com Pedro e Marília como usuários de teste) e pôr o ID no `.env` | Pedro | Até seg 28 | Só escopos de identidade, sem verificação do Google |
| D10 | Segundo chip pré-pago para fazer o papel da profissional, fora de qualquer WhatsApp. Passar os IDs do número e da conta do WhatsApp Business | Pedro | Até sex 02 | Necessário para o dia de adicionar número (seg 05) |
| D6 | Domínio + servidor na nuvem | Pedro | **Adiado** (decisão de 25/09) | MVP segue local (plano B). O código fica pronto para a nuvem; o deploy é decidido depois. O webhook exige HTTPS público |

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

**Reportar:** status da Meta (número, verificação);
o que a Marília definiu; primeiros números do conjunto de teste.

**Perguntar ao Thiago:** se ele espera número medido de acurácia da
triagem ou só a descrição do mecanismo. **Deploy:** se o MVP de 09/10
precisa estar no ar (domínio, VPS, HTTPS) ou se a demo pode rodar local
no simulador; a resposta decide a segunda 28 (decisão aberta 5).

**Se não bateu:** preço, tom e RAG podem escorregar para a semana 2.
Modelo de dados, pipeline e triagem não.

---

## 4. Semana 2: 28/09 a 02/10 (~18h)

**Plano B (decidido em 25/09): sem deploy por enquanto.** O MVP roda
local, mas o código fica pronto para ir para a nuvem quando o Pedro
decidir (ver "Pronto para a nuvem" abaixo).

**Objetivo:** um painel protegido por login com Google, com cadastro
em etapas, inbox e alertas, e o WhatsApp real recebendo pelo webhook
(túnel), tudo rodando local.

| Dia | ~h | Trabalho |
|---|---|---|
| Seg 28 | 3,5 | Login com Google (só identidade), e-mails autorizados no `.env`, sessão em cookie, todas as rotas de gestão protegidas com checagem de dono, rate limit; tela de login. O `/chat/simulate` vira o simulador autenticado do painel. Pedro: D9 |
| Ter 29 | 3,5 | Cadastro em etapas (perfil completo libera o painel, `slug` gerado do nome, aceite das regras fixas). Triagem de mensagens quebradas (a triagem olha as últimas mensagens do contato juntas) |
| Qua 30 | 4 | Painel: inbox (lista de conversas, estado, "necessita atenção"; assumir, responder e devolver já existem). **Sessão B:** enviar resultados e transcritos da triagem para a Marília revisar |
| Qui 01/10 | 4 | Painel: tela de alertas (trecho, horário, canal, revisado, trilha) + atualização a cada 10s. **Checkpoint** |
| Sex 02 | 3,5 | Rever as quatro lacunas do modelo para o WhatsApp (número por profissional primeiro). Webhook (verificação, assinatura, deduplicação, roteamento pelo número, envio da resposta) testado com túnel temporário. Troca da lista "nunca dizer" pela da Marília. Fechamento. Pedro: D10 |
| Sáb/Dom 03–04 | reserva | Deve ser usada: é a folga que sobrou depois de 26/09. Prioridade: webhook e alertas |

Contêineres e guia de deploy ficam para depois de 09/10; as regras de
"Pronto para a nuvem" continuam valendo no código desde já.

**O que fica bloqueado sem deploy:** só **receber** mensagens reais do
WhatsApp (o webhook exige HTTPS público). Enviar funciona do computador
local. O código do webhook pode ser escrito e testado com um túnel
temporário quando o Pedro quiser; a demo roda no simulador (seção 1).

### Pronto para a nuvem

Regras para que o deploy, quando decidido, seja só configuração:

- Toda configuração vem do `.env` (banco, chaves, e-mail, URLs, CORS);
  nada de endereço fixo no código além dos padrões de desenvolvimento.
- Banco só muda por migração do Alembic.
- Arquivos que precisam sobreviver (ChromaDB) ficam numa pasta
  configurável, que vira um volume no servidor.
- Login preparado para painel e API no mesmo domínio (cookie
  `httpOnly`, `Secure` ligado por configuração).
- Nenhum passo manual que só funcione no Windows do Pedro.

**Checkpoint de quinta 01/10:** o número da Meta saiu? A semana está no
prazo? Se não, a agenda passa para o modo degradado (seção 1).

**Para o Thiago:** decisões de arquitetura já tomadas (falha fechada,
assinatura do webhook, LGPD), em uma página.

### Fechamento de sexta 02/10

**Mostrar:** mensagem entrando (no WhatsApp real, ou no simulador se não
houver número), triagem, alerta no painel com trilha de auditoria,
e-mail de alerta chegando para a Marília fora do painel, e a Marília
respondendo pelo painel.

**Reportar:** números da triagem revisados por ela, com os falsos
negativos analisados um a um.

**Perguntar ao Thiago:** se a amostra basta para o capítulo de
resultados.

**Se não bateu:** inbox simplificado (lista, conversa, responder), sem
filtros. A agenda entra degradada.

---

## 5. Semana 3: 05 a 09/10 (~16h)

**Objetivo:** adicionar número pelo painel, agenda enxuta, testar com a
Marília, congelar e ensaiar.

| Dia | ~h | Trabalho |
|---|---|---|
| Seg 05 | 3,5 | Adicionar número pelo painel: adicionar à conta, código por SMS, conferir, registrar, ligar à profissional. Teste com o segundo chip (D10), contando os registros (limite de 10 em 72h) |
| Ter 06 | 4 | Agenda enxuta (service account): leitura de disponibilidade, oferta de até 3 horários na conversa, evento provisório. Aprovar/recusar no painel só se couber |
| Qua 07 | 3,5 | **Sessão C:** teste supervisionado com a Marília (painel + fluxo + os 11 cenários). Guardrails e prompt injection testados de propósito, teto de custo, limite por contato. Teste de restauração do backup |
| Qui 08 | 3,5 | Correções da sessão C. **Congelar o código ao meio-dia.** Dados sintéticos de demo, ensaio cronometrado, **vídeo de backup** |
| Sex 09 | | Demo para o Thiago |

**Para o Thiago:** metodologia de teste da triagem (cenários, falso
positivo, falso negativo) em uma página.

### Roteiro da demo (ensaie nesta ordem)

1. Profissional entra com o Google, completa o cadastro e adiciona o número de WhatsApp (código por SMS)
2. Lead novo manda "oi" para esse número: aviso de IA + apresentação
3. Pergunta sobre a abordagem: resposta via RAG
4. "Quanto custa?": tratamento do preço
5. Escolhe horário: evento provisório aparece no Google Calendar
6. Outra conversa, mensagem com sinal de risco: mensagem fixa, alerta no painel e e-mail para a Marília
7. Painel: alerta aberto, trecho, marcar como revisado, trilha de auditoria
8. Pessoa volta a conversar: retomada sem reativar o protocolo
9. Números do teste de triagem

### Fechamento de sexta 09/10

**Mostrar:** o roteiro acima, completo.

**Perguntar ao Thiago:** duração e formato da demo na defesa; o que ele
gostaria de ver que ainda falta.

---

## 5b. Reta final: 13 a 15/10 (feedback de 30/09 + o que faltou da semana 3)

Decidido em 12/10 (Pedro): **a demo do app fecha na quinta 15/10.**
Junta o que ficou da semana 3 (nada foi commitado depois de 30/09) com
o feedback do orientador e da professora na apresentação de 30/09. O
que é só texto do TCC (fluxos, custos, identificação, por que LLM) vai
para a semana de 19/10, seção 6.

**Já verificado em 12/10:** o WhatsApp continua respondendo depois da
cobrança das mensagens de serviço pela Meta (01/10), sem verificação do
negócio. Abaixo de ~1.000 mensagens por mês por número não deve haver
custo; mesmo assim, cadastrar cartão na conta (tarefa do Pedro) evita o
erro 131042 se a franquia não valer.

**O que estava planejado para 09/10, conferido em 12/10:**

| Item do escopo de 09/10 | Situação |
|---|---|
| Bot: aviso de IA, apresentação, RAG, preço, triagem, retomada, handoff, pré-agendamento | Feito |
| Painel: login com Google, cadastro em etapas, conversas, alertas com trilha, "necessita atenção", aprovar/recusar horário, base e tom | Feito |
| Canal: assinatura do webhook, deduplicação, espera que junta mensagens, app publicado | Feito |
| LGPD: mensagens e telefone criptografados, política de privacidade publicada | Feito |
| Adicionar número pelo painel (seg 05) | **Construído em 13/10** ([conectar o WhatsApp](funcionalidades/conectar-whatsapp.md)), testado com a Meta simulada; falta o teste com o segundo chip |
| Limite por contato e teto de custo (qua 07) | **Falta** |
| Guardrails e prompt injection testados de propósito (qua 07) | **Feito em 13/10:** 22 ataques e 31 mensagens sensíveis no modelo real (injection 21/22, sensíveis 27/31, [resultados](resultados-testes/)); corrigida a mensagem vazia quando o modelo recusa. O que sobrou vai para a sessão C |
| Teste de restauração do backup (qua 07) | **Falta.** Não há script de backup |
| Sessão C com a Marília; aprovação dos textos fixos (handoff, agenda, tipo não suportado); lista de "nunca dizer" dela no lugar da provisória | **Falta** |
| Números da triagem para a demo | Existe o resultado v1 (23/09); **reexecutar** depois das mudanças de 27 e 30/09 |
| Congelar, dados sintéticos, ensaio, vídeo de backup (qui 08) | **Falta** |
| Deploy com HTTPS | Não é pendência: plano B de 25/09 (roda local, código pronto para a nuvem) |

| Dia | Trabalho | Origem |
|---|---|---|
| Ter 13 | **Limites por contato:** no máximo 2 pedidos de horário pendentes por pessoa (hoje dá para reservar um por dia, sem teto, e travar a agenda por 24h); teto de mensagens por número por hora, acima dele a camada 1 da triagem continua e o modelo não é chamado (texto fixo). **Teto de custo:** gravar os tokens de cada chamada (sem conteúdo), somar por dia e, acima do teto do `.env`, parar de chamar o modelo de resposta e avisar a profissional; a triagem nunca para. Cache do prompt na parte fixa. **Backup:** script de `pg_dump` e restauração testada. **Falha de envio** pela Meta marcada na conversa. **Troca do nome**, se já escolhido | 09/10 (limite, teto, backup) + feedback (custo, injection, nome) |
| Qua 14 | **Adicionar número pelo painel**: construído em 13/10; na quarta, só o teste com o segundo chip (roteiro em `funcionalidades/conectar-whatsapp.md`). **Quem chega desesperado** (seção 9, aberta 6): de manhã o Pedro pergunta à Marília o que a SelenIA pode fazer sem tratar; à tarde, implementar a partir da resposta (ou da proposta, se ela não responder a tempo), com textos marcados como pendentes de aprovação e cenários no conjunto de respostas sensíveis. *(Remarcar e cancelar: adiantado, feito em 13/10.)* | 09/10 (número) + feedback (o que a IA pode dizer) + Pedro (13/10) |
| Qui 15 | Manhã: ~~conjuntos de teste~~ (*adiantado, feito em 13/10*); depois da sessão C, ajustes no prompt e nova rodada dos conjuntos, **reexecução da triagem**. **Sessão C com a Marília:** textos fixos, "nunca dizer" dela, cenários, e a validação do que foi feito na quarta para quem chega desesperado (seção 9, aberta 6). **Congelar às 16h.** Dados sintéticos, ensaio cronometrado, **vídeo de backup** | 09/10 (guardrails, sessão C, demo) + feedback (o que a IA pode dizer, injection) |

**Mudança de 14/10 (Pedro):** a quarta não teve trabalho; **tudo o que
estava na quarta passa para a quinta 15**, junto com o que já era da
quinta. Ordem proposta para o dia: (1) de manhã, reexecução da triagem
rodando enquanto o Pedro fala com a Marília; (2) sessão C, que agora
também decide quem chega desesperado; (3) implementar o que sair da
sessão (desesperado + ajustes no prompt) e nova rodada dos conjuntos;
(4) teste do segundo chip; (5) congelar, dados sintéticos, ensaio e
vídeo. Se apertar, corta nesta ordem: teste do chip (o vídeo mostra o
fluxo até o pedido de código), depois o item de quem chega desesperado
vira texto do TCC com a decisão da Marília registrada.

**Decisão de 15/10 (Pedro):** todas as funções do app estão construídas;
o app fecha hoje como funcional. Hoje só o que é funcional: teste do
segundo chip (única função nunca usada com a Meta de verdade), commit e
preparação da demo (dados sintéticos, ensaio, vídeo). **A partir de
16/10 começa a parte escrita**, e o que é comportamento da SelenIA vai
em paralelo com o texto: sessão C e aprovação dos textos fixos (antes de
qualquer uso real com pacientes, não antes da demo), lista de "nunca
dizer" da Marília, quem chega desesperado (aberta 6), ajustes no prompt
com nova rodada dos conjuntos e reexecução da triagem (números para os
resultados).

**Tarefas do Pedro:** segundo chip em mãos na quinta; perguntar à Marília, na quarta de manhã, como a SelenIA pode ajudar quem chega desesperado sem tratar; escolher o nome
novo (pesquisar INPI e "nome + chatbot"); cadastrar cartão no WhatsApp
Manager; marcar a sessão C com a Marília para quinta de manhã e pedir a
lista de "nunca dizer" dela antes.

**Fora da quinta (decisão de 12/10):**
- Palavra-chave ou confirmação por e-mail para identificar o paciente:
  o cancelamento como pedido já impede o estrago principal; o resto vai
  para o texto, como análise de ameaça e trabalho futuro.
- Comparar a triagem com Haiku 5.5 e com um modelo local: experimento
  para os resultados, na semana de 19/10, se houver tempo.
- Omnichannel e Chatwoot: só WhatsApp na defesa; trabalho futuro.

**Roteiro da demo:** o da seção 5, com dois passos novos: depois do
passo 5, a pessoa pede para remarcar e a profissional confirma no
painel; no passo 9, além da triagem, os números dos testes de prompt
injection e de respostas sensíveis.

**Ordem de corte se apertar:** troca do nome (fica só no texto);
remarcar e cancelar; adicionar número pelo painel (a demo usa o número
já conectado e o vídeo mostra o fluxo até o pedido de código); falha de
envio marcada. **Não corta:** limites por contato, teto de custo,
backup testado, testes de injection e de respostas sensíveis, sessão C,
vídeo de backup.

---

## 6. Depois de 09/10: artigo, extras e defesa

O MVP congela em 08/10. Depois de 09/10 o foco é o artigo; em paralelo,
entram só os extras listados na seção 1 ("Fica para depois de 09/10").

| Semana | Foco |
|---|---|
| 13 a 15/10 | Reta final da demo do app (seção 5b) |
| 12 a 16/10 | Feedback do Thiago; redação do artigo; extras (cadastro com aprovação e publicação no Google, aprovar/recusar agendamento se não coube, contêineres e guia de deploy, PIX fino, retenção agendada e log de acesso); piloto supervisionado com a Marília, só depois da aprovação dela e do aviso de IA aprovado |
| 19 a 23/10 | Polir a demo da defesa (roteiro final, dados sintéticos, vídeo); métricas e resultados no TCC. Ajustes no atendimento de quem chega desesperado, se a sessão C pedir. Textos pedidos em 30/09: título e objetivo real do chatbot; mapa de opções e diagramas de fluxo; o que a IA pode incentivar ou dizer e como é contido; custo mensal estimado e medido (com a cobrança da Meta desde 01/10 e a opção de modelo local); ameaça de quem pega o celular do paciente; por que LLM e não um bot de menu (com a comparação camada 1 x camada 2 da triagem como evidência) |
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
  script; a versão agendada e o log de acesso ficam para depois de 09/10.
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
| E-mail de alerta não chega (spam, SMTP fora) | baixa | Aviso no painel; o evento `notify_failed` fica na trilha do alerta |
| Semana 2 estoura | alta | Inbox simplificado; agenda degradada |
| Semana 3 estoura | média | Agenda vira evento criado manualmente na demo |
| API da Claude cai na demo | baixa | Vídeo de backup do dia 8 |
| Limite de registro do número (10 em 72h) ou nome de exibição pendente na Meta | média | Contar os registros; último registro de ensaio até ter 06; o vídeo de backup mostra o fluxo |
| Segundo chip não chega até sex 02 | baixa | Mostrar o fluxo até o pedido de código e usar o chip da MarIA como número já registrado |

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

**Resolvidas em 24/09 (Pedro):**
1. Pedido para falar com a profissional: se ela estiver "Em consulta"
   (botão no painel, com duração e fim automático), aviso fixo de que
   ela está em atendimento e o bot segue ajudando; senão, o bot para e
   ela assume. O aviso só aparece quando a pessoa pede, não na abertura.
2. Quem recusa falar com um bot recebe uma mensagem fixa de
   compreensão (sem números de emergência), o bot para e a profissional
   recebe um alerta (nível próprio, fora das métricas da triagem).
3. "Nunca dizer" fixo ganhou dois itens: nada fora do atendimento
   (tarefas, códigos, conhecimentos gerais) e nenhuma mudança de papel
   ou revelação das instruções pedida na conversa.

**Resolvidas em 26/09 (Pedro):**
1. O alerta para a profissional vai por e-mail e pelo painel (no futuro,
   pela notificação do app). Não sai pelo WhatsApp, então a Meta não
   precisa de template de alerta nem de forma de pagamento: o bot só
   responde quem escreveu primeiro.
2. Verificação do negócio na Meta não é necessária para o TCC. Mesmo
   com o CNPJ da Marília disponível, fica sem verificação até a defesa
   para não aumentar o escopo; coexistência continua trabalho futuro.
3. Login com Google (só e-mails autorizados), cadastro em etapas e
   adicionar número pelo painel entram no MVP de 09/10. A agenda entra
   enxuta e o guia de contêineres fica para depois de 09/10 (seção 0,
   item 14).
4. O profissional responde às pessoas **só pelo painel da MarIA**. O
   número conectado fica dedicado à MarIA e sai do app do WhatsApp (sem
   coexistência). Quem quiser usar o número que já atendia precisa
   apagar a conta do WhatsApp dele no celular antes; o histórico antigo
   não vem. Por isso as telas de conversas e alertas precisam funcionar
   no navegador do celular.

**Resolvida em 27/09 (Pedro):**
1. Linguagem neutra de gênero em telas, regras, e-mails e prompt, por
   reescrita da frase e não com "o/a" (regra no CLAUDE.md).
2. Tela de Conversas (feita em 27/09, adiantada da quarta 30): situação
   própria "Aguardando você" para quem pede a profissional ou recusa o
   bot; e-mail sem conteúdo quando alguém pede para falar com ela;
   conversas do simulador na lista com a etiqueta "Teste". A janela de
   24h trava a resposta (sem modelo pago de retomada; isso fica como
   trabalho futuro).
3. Mensagens quebradas (feito em 27/09): a camada 1 da triagem também
   roda nas últimas 3 mensagens do contato em até 5 minutos, juntas,
   mesmo com resposta da MarIA entre elas.
4. **Espera antes de responder** (entra com o webhook, sexta 02): a
   WhatsApp Cloud API não avisa quando o contato está digitando. Então,
   a cada mensagem, o sistema espera alguns segundos (proposta: 6 s,
   recomeçando se chegar outra); quando a pessoa para, junta as
   mensagens e responde uma vez só, mostrando "digitando…" para ela
   enquanto isso. A triagem continua rodando em cada mensagem assim que
   chega: a espera nunca atrasa a mensagem de emergência. A junção do
   item 3 fica como segunda proteção.
5. Webhook feito em 27/09 (adiantado da sexta 02), com a espera do item
   4. Túnel com **endereço fixo** (ngrok gratuito,
   `shininess-oxygen-giddily.ngrok-free.dev`), cadastrado uma vez na
   Meta; pelo túnel só passa `/webhook/`. Avisos de entregue e lido
   fora do MVP. Teste da Meta com assinatura real: 200. **Falta
   publicar o app** (a Meta só entrega mensagens reais com o app
   publicado), o que pede um link público de política de privacidade.

**Resolvida em 28/09 (Pedro):**
1. **Agenda pelo painel, não por service account.** A tela Agenda tem
   o botão "Sincronizar com o Google Agenda" (permissão OAuth da conta
   que ela escolher) e o horário de atendimento (dias e intervalos). A
   MarIA consulta os horários livres por uma ferramenta, só quando a
   conversa pede, e oferece até 3; quem confirma é a profissional.
   Permissão mínima: só livre/ocupado (a MarIA nunca vê o nome de um
   evento). Precisa do `GOOGLE_CLIENT_SECRET` no `.env` e dos escopos
   no Google Cloud.
2. **A MarIA reserva, a profissional confirma** (adiantado de ter 06).
   Quando a pessoa escolhe, a MarIA cria o evento "Sessão (a confirmar)"
   e a profissional confirma ou recusa na tela Agenda; a pessoa recebe
   texto fixo com a decisão. Evento com **nome e telefone** do paciente.
   Reserva segura **24h**; depois expira e a profissional recebe e-mail.
   Duas pessoas no mesmo horário: trava por profissional no banco +
   índice único. Pede a permissão `calendar.events` (sensível: abrir a
   mais pessoas exige verificação do Google). Textos fixos de
   confirmação e recusa aguardam a Marília.
3. **Depois do primeiro teste real (Pedro):** a MarIA vê todos os
   horários livres (grade de 30 min), com **máximo de sessões por dia**
   configurável; a duração da sessão vai sempre no prompt; e a tela
   Agenda ganhou o **calendário da semana**, onde a profissional vê os
   eventos e marca sessões ou compromissos. Cada pessoa pode ter **uma
   sessão por dia**, em quantos dias quiser.

**Resolvidas em 12/10 (Pedro, a partir do feedback de 30/09):**
1. **O nome MarIA muda:** o governo já usa "MarIA" para um assistente
   de chatbot. Continua um nome só, do produto, igual em todas as
   contas. Nome novo a escolher.
2. Omnichannel e Chatwoot ficam fora: na defesa, só WhatsApp.
3. A demo do app fecha na quinta 15/10 (seção 5b). Textos do TCC
   pedidos no feedback vão para a semana de 19/10.
4. Identificação do paciente: o risco é alguém com o celular dele
   (ex.: parceiro) cancelar ou falar em nome dele. Resposta no MVP:
   remarcar e cancelar são sempre pedido confirmado pela profissional.
   Confirmação por e-mail não resolve sozinha (o e-mail costuma estar no
   mesmo celular); palavra-chave combinada fica como trabalho futuro.
5. Prompt injection e respostas sensíveis passam a ter conjunto de teste
   próprio, com números no TCC, além das regras do prompt.
6. **Limites por contato** (feito em 12/10): até 4 pedidos de horário
   aguardando confirmação e 50 mensagens por hora, **por pessoa**, nunca
   da conta inteira (muita gente escrevendo ao mesmo tempo não pode
   travar ninguém). Acima do limite de mensagens, só a camada 1 da
   triagem roda e a pessoa recebe um aviso fixo uma vez.
7. **Sem teto de custo da conta inteira** (Pedro): um teto da conta
   podia travar todo mundo num dia movimentado. O custo passa a ser
   medido (tokens por chamada, `scripts/custo.py`) e a parte fixa do
   prompt vai com cache (feito em 12/10).
8. **Backup** com restauração testada (feito em 12/10,
   `scripts/backup.py`): todas as tabelas batendo.
9. **Nome novo: SelenIA** (Pedro, 12/10; troca feita em 13/10). Busca
   rápida não achou chatbot nem app de saúde com esse nome; conferir no
   INPI fica com o Pedro. Este plano mantém "MarIA" onde conta o que
   aconteceu antes da troca.
10. **Remarcar e cancelar** (adiantado de qua 14, feito em 13/10):
    remarcar apaga a data antiga e marca a nova; cancelar cancela a
    sessão de vez. Os dois só valem quando a profissional confirmar
    (sessão confirmada); pedido ainda sem confirmação a pessoa desfaz na
    hora. Também feitos em 13/10: falha de envio marcada ("Não
    entregue") e troca do nome para SelenIA.

**Abertas:**
1. Número brasileiro: usar uma linha sem uso da casa (dedicada ao MVP), desde que receba SMS/ligação e esteja livre de WhatsApp. Confirmar isso na segunda.
2. Fins de semana entram como capacidade ou ficam livres?
3. Aviso de IA e consentimento: recomendação de 23/09 é aceite explícito
   antes do bot responder (triagem roda mesmo antes do aceite). Validar
   com o Thiago.
4. Paciente em acompanhamento ativo com alerta de emergência: a Marília
   quer "algo a mais" além do alerta padrão. Definir o quê.
5. **Quando fazer o deploy na nuvem.** Em 25/09 ficou decidido seguir
   sem deploy (plano B), com o código pronto para a nuvem. Falta decidir
   quando e onde. Afeta D6, D8 e o recebimento real pelo WhatsApp.
6. **Como ajudar quem chega desesperado, sem tratar** (Pedro, 13/10).
   Muita gente procura terapia no pior momento ("preciso de ajuda
   urgente", "não aguento mais"), sem risco à vida. Hoje a triagem marca
   "sofrimento intenso" (conversa com "necessita atenção") e o prompt
   manda acolher e seguir o atendimento normal; não há nada além disso.
   Falta definir, **com a Marília** (é decisão clínica), o que a SelenIA
   pode fazer sem virar atendimento terapêutico. Ideias para levar:
   - frases de acolhimento escritas ou aprovadas por ela, em vez de
     deixar o modelo improvisar;
   - oferecer o horário livre mais próximo logo de cara, ou um encaixe;
   - avisar a profissional na hora (e-mail, como no pedido para falar
     com ela), não só a marcação no painel;
   - lembrar do CVV (188) como apoio para conversar agora, sem tratar a
     pessoa como emergência;
   - o que ela **não** pode fazer: técnicas de respiração ou de
     enfrentamento, perguntas sobre a história, promessas de que vai
     melhorar.
   **Na quarta 14** (Pedro, 13/10): o Pedro pergunta à Marília de manhã
   e a implementação sai à tarde, com cenários novos no conjunto de
   respostas sensíveis; a sessão C (qui 15) valida.

**Feedback do teste de 18/10** (Pedro, 19/10): a SelenIA prometia "vou
perguntar ao Pedro" sem nada chegar a ele, não sabia as formas de
pagamento e não tinha como tratar alguém que diz ser "paciente
especial". Decidido e feito em 19/10:
- ferramenta `avisar_profissional`: e-mail e "Aguardando você" com o
  motivo, sem parar o bot; o prompt só deixa prometer junto com ela
  ([pedidos para a profissional](funcionalidades/pedidos-para-a-profissional.md));
- formas de pagamento no Perfil, numa lista de escolha múltipla;
- tela Clientes: cliente ativo automático ao confirmar sessão, tirar e
  pôr na lista, e permissão para os dias especiais que a profissional
  marca para cada cliente especial (no dia especial, qualquer horário
  livre, e sem limite de sessões por dia; primeiro foram intervalos
  iguais para todos, trocados no mesmo dia a pedido do Pedro)
  ([clientes e horário especial](funcionalidades/clientes-e-horario-especial.md)).
- o e-mail do pedido não leva resumo do que a pessoa perguntou: o Pedro
  preferiu manter a regra de nenhum conteúdo de conversa em e-mail (LGPD).
Funcionalidade nova depois de o app ter sido fechado como funcional em
15/10: entra no texto do TCC como resposta ao teste com usuário.

**"Em consulta" depois do teste de 03/11** (Pedro, 03/11/2026): no teste
com a Marília pelo WhatsApp, o botão "Em consulta" quase não fazia
diferença (ligado tarde, a SelenIA não sabia dele, e-mails no meio da
sessão). Decidido e feito em 03/11:
- liga sozinho durante um compromisso do Google Agenda; o botão continua
  para sessão fora da agenda ou para estender;
- a SelenIA recebe "em atendimento até HH:MM" no prompt;
- as mensagens fixas de pedido e recusa dizem até que horas;
- em consulta, os e-mails de pedido viram um resumo único no fim;
  alertas de segurança continuam na hora;
- recusado: resposta automática nas conversas que ela assumiu (a
  SelenIA continua em silêncio nelas).
Detalhes em [Handoff e "Em consulta"](funcionalidades/handoff-e-em-consulta.md).

**Cliente especial lido a cada mensagem** (Pedro, 04/11/2026): a condição
especial pode ser ligada com a conversa em andamento, e isso não pode
depender de o modelo lembrar de consultar. Em assunto de horário, o
pipeline lê a agenda e a permissão a cada mensagem e põe o resultado no
prompt. No mesmo dia, o Pedro decidiu que a antecedência mínima de 12
horas não vale para cliente especial; todo pedido provisório passa a
vencer na hora da sessão, se isso vier antes das 24 horas. Pedido com
menos de 12 horas manda o e-mail mesmo "Em consulta", e a pessoa é
avisada pela conversa quando um pedido vence. Detalhes em
[Clientes e horário especial](funcionalidades/clientes-e-horario-especial.md).

**Resolvida em 15/11 (Pedro):** sessão confirmada ganha um link do
Google Meet, criado no evento da agenda da profissional e enviado à
pessoa junto da confirmação. Na troca, a data antiga sai com o link
dela e a nova ganha outro; no cancelamento, a mensagem avisa que o link
não vale mais. Detalhes em [Agenda](funcionalidades/agenda.md).

**Resolvida em 15/11 (Pedro):** o menu Conversas mostra quantas
mensagens das pessoas a profissional ainda não leu, como o menu Alertas
faz com os alertas sem revisar; cada conversa da lista mostra o dela.
Detalhes em [Conversas](funcionalidades/conversas.md).

**Resolvida em 15/11 (Pedro):** a tela WhatsApp ganha o botão vermelho
**Remover número**, com confirmação na própria tela. Detalhes em
[Conectar o WhatsApp](funcionalidades/conectar-whatsapp.md).


**Decidida em 15/11 (Pedro):** a banca testa a SelenIA numa conta de
demonstração (perfil fictício da Camila Nogueira, número +55 21
98487-0438), que entra por **e-mail e senha** para não depender da
janela do Google na defesa. O cadastro continua fechado por convite.
Detalhes em [Login com Google](funcionalidades/login-com-google.md).
