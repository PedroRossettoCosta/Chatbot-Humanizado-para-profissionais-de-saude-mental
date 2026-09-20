# Levantamento de Requisitos, Priorização de Features e MVP

> Gerado após a orientação com o Thiago (16/09/2026): a próxima etapa é
> agilizar o planejamento — lista de features priorizadas por impacto
> no negócio, mapeamento de requisitos, definição do MVP, e então
> começar a construir o app web pra rodar localmente. A ordem de
> prioridade ainda precisa ser confirmada com a Marília antes de virar
> compromisso (ver seção 9).
>
> Base usada: `Entrevista_Marilia_TCC.md` (dados de negócio),
> `Entrevista_Marilia_Protocolo_Seguranca — Marília.docx` (protocolo de
> segurança, respondido em 16/09/2026), `planejamento-projeto.md`
> (arquitetura e roadmap já combinados), e o código atual do backend.

---

## 1. Como a priorização foi feita

Três critérios, nessa ordem:

1. **Segurança/ética não é negociável** — o módulo de triagem é P0
   sempre que há dado suficiente pra construí-lo com responsabilidade.
   Não entra no MVP nada que dependa de detecção de risco ainda mal
   definida.
2. **Impacto real no negócio da Marília**, extraído da primeira
   entrevista (não é achismo):
   - **2 em cada 10 leads somem por demora** na resposta — favorece
     qualquer feature que responda instantaneamente.
   - **A maioria some depois que ela informa o preço** — ela nunca
     quer que o preço seja dado de cara; a resposta do bot sobre
     valores precisa seguir esse padrão dela, não empurrar preço.
   - **O agendamento é lento** (ela responde de manhã, só tem vaga à
     tarde, o lead esfria esperando) — favorece pré-agendamento
     dentro da conversa, não depois por fora.
   - **A reserva só fecha depois do pagamento** — favorece validação
     rápida de PIX, mas isso já era sabido como mais complexo
     (visão computacional) e continua não sendo prioridade imediata.
3. **Escopo de uma defesa de TCC** — o que dá pra demonstrar
   funcionando de ponta a ponta com um canal simulado ou WhatsApp de
   teste, sem depender de infraestrutura de produção (cobrança,
   onboarding self-service, número de WhatsApp brasileiro definitivo).

Prioridades usadas nas tabelas abaixo:

- 🔴 **P0 — MVP.** Sem isso o protótipo não demonstra a proposta de
  valor nem os princípios éticos do projeto.
- 🟡 **P1 — Pós-MVP, curto prazo.** Fortalece o produto, mas a defesa
  não depende disso.
- 🟢 **P2 — Trabalho futuro.** Já declarado como fora do escopo da
  defesa em `planejamento-projeto.md`, ou depende de decisão ainda em
  aberto.

---

## 2. Features do BOT (o que o paciente/lead vê, pelo canal de mensagens)

| ID | Feature | Prioridade | Por quê |
|---|---|---|---|
| BOT-01 | Resposta automática imediata a qualquer mensagem recebida | 🔴 P0 | Ataca direto o "2 em 10 somem por demora" |
| BOT-02 | Aviso automático de que é um assistente de IA (não uma pessoa) | 🟡 P1 | **Já implementado no código**, mas a Marília disse na entrevista que ainda não decidiu como quer que seja comunicado — precisa da aprovação dela antes de virar definitivo (ver seção 8) |
| BOT-03 | Apresentação da profissional e da abordagem terapêutica dela | 🔴 P0 | Pergunta recorrente ("é psicóloga ou psicanalista?", "como funciona a terapia") |
| BOT-04 | Responder dúvidas via RAG (abordagem, atende online, duração, diferença curso/terapia, nota fiscal) | 🔴 P0 | Já é o núcleo do sistema (RAG + documentos), maior parte já construída |
| BOT-05 | Tratamento cuidadoso da pergunta de preço (nunca informar de cara) | 🔴 P0 | Maior ponto de perda de conversão apontado por ela — é uma regra de tom de voz, não uma feature nova de infraestrutura |
| BOT-06 | **Triagem de segurança — nível emergência** (detecta indicação clara ou ambígua de risco à vida, interrompe o fluxo normal, envia mensagem fixa aprovada com SAMU 192 / 190 / CVV 188) | 🔴 P0 | Antes bloqueado por falta de protocolo — **agora desbloqueado**, critérios e texto já aprovados pela Marília (seção 7 e 8) |
| BOT-07 | **Triagem de segurança — nível "sofrimento intenso"** (sinaliza para revisão humana sem interromper o fluxo nem acionar o protocolo de emergência) | 🔴 P0 | Distinção explícita que ela fez: sofrimento relacional intenso (comum no nicho dela) ≠ emergência. Sem esse segundo nível, o sistema ou ignora sofrimento real ou dispara alarme falso o tempo todo |
| BOT-08 | Retomada normal da conversa depois de um alerta, se a pessoa volta sem sinal de risco | 🔴 P0 | Ela foi explícita: a pessoa pode voltar depois pra agendar normalmente, o bot não deve tratá-la como "caso encerrado" |
| BOT-09 | Pré-agendamento com horários disponíveis (Google Calendar) dentro da própria conversa | 🟡 P1 | Ataca o "agendamento lento" e o "lead esfria esperando", mas depende de integração já mapeada como mais complexa |
| BOT-10 | Validação de comprovante PIX (visão computacional) | 🟢 P2 | Já listado como "não priorizado" no planejamento; mantém-se assim |
| BOT-11 | Handoff explícito para atendimento humano a pedido do usuário | 🟡 P1 | Reforça o princípio ético (a IA nunca substitui a profissional), mas não é bloqueante pra demonstrar o conceito |
| BOT-12 | Atendimento no WhatsApp real (produção) | 🟡 P1 | Já em andamento; limitado hoje pela restrição de número EUA→BR já documentada. MVP pode rodar 100% via canal simulado |
| BOT-13 | Atendimento em Instagram e TikTok | 🟢 P2 | Volume ainda baixo (8 msg/semana Instagram, TikTok ainda não gerenciado); ela mesma disse que quer aplicar depois que o volume crescer |
| BOT-14 | Follow-up automático para leads que pararam de responder | 🟢 P2 | Ideia nova a partir da dor relatada ("param de responder e ela precisa fazer follow-up manual"); não estava no escopo original — vale propor como próximo passo, não como parte da defesa |

---

## 3. Features do PAINEL WEB (o que a profissional vê e usa)

| ID | Feature | Prioridade | Por quê |
|---|---|---|---|
| WEB-01 | Configurar tom de voz e mensagens padrão do bot | 🔴 P0 | **Já implementado** (`Configuração do Assistente`) |
| WEB-02 | Upload e gerenciamento da base de conhecimento (documentos) | 🔴 P0 | **Já implementado** (`routers/documents.py`) |
| WEB-03 | Inbox de conversas (ver o que o bot está conversando, por canal) | 🔴 P0 | Sem isso ela não consegue confiar no sistema nem revisar transcritos — pré-requisito que ela mesma colocou antes de aceitar rodar com pacientes reais |
| WEB-04 | Tela de Alertas de Segurança — nível emergência (trecho, horário, canal, acesso à conversa completa ou link direto, marcar como revisado) | 🔴 P0 | Exigência explícita dela: "quero ter acesso à conversa inteira ou um link que me leve direto até ela" |
| WEB-05 | Marcação "necessita atenção da Marília" dentro do inbox de conversas (nível sofrimento intenso, não é alerta de risco) | 🔴 P0 | Segundo nível de triagem que ela pediu — sem essa distinção visual, vira tudo alerta de risco ou nada vira alerta |
| WEB-06 | Notificação em tempo real quando um alerta de risco disparar | 🟡 P1 (MVP local: notificação dentro do próprio painel / e-mail) | Ela pediu preferencialmente por WhatsApp — mas isso depende do número de produção que ainda não está resolvido; pra rodar localmente, um alerta imediato dentro do painel (e endpoint pronto pra plugar WhatsApp depois) cobre o mesmo requisito sem depender da infraestrutura de produção |
| WEB-07 | Dashboard com métricas (mensagens hoje, leads, taxa de conversão) | 🟡 P1 | Reforça a proposta de valor, mas não é o que garante segurança nem resolve a dor de negócio mais crítica |
| WEB-08 | Agenda integrada ao Google Calendar (aprovar/recusar pré-agendamento) | 🟡 P1 | Junto com BOT-09 |
| WEB-09 | Pagamentos / validação de PIX | 🟢 P2 | Mesma razão do BOT-10 |
| WEB-10 | Login/cadastro completo de profissionais | 🟢 P2 | Já declarado como trabalho futuro em `planejamento-projeto.md` |
| WEB-11 | Planos / assinatura / cobrança (Stripe) | 🟢 P2 | Idem |
| WEB-12 | Exportar/excluir dados da profissional (LGPD, portal de autoatendimento) | 🟡 P1 | A lógica de retenção já existe no backend (script manual); falta só a interface — mas não bloqueia a defesa |

---

## 4. Mobile companion

Escopo e telas já documentados em `explicacao.md`. Para efeito de
priorização: **o mobile inteiro é 🟢 P2** — é um "acompanhador", faz
sentido só depois que o painel web (o produto completo) estiver
funcionando de ponta a ponta. Os protótipos do Stitch já dão a
direção visual; não há necessidade de decidir isso agora.

---

## 5. Requisitos funcionais e não funcionais

Mapeamento formal, útil pra seção de requisitos do TCC. Cada RF
referencia o(s) ID(s) de feature correspondente(s).

### Requisitos funcionais

| RF | Descrição | Feature(s) |
|---|---|---|
| RF01 | O sistema deve responder automaticamente a qualquer mensagem recebida em tempo real | BOT-01 |
| RF02 | O sistema deve responder dúvidas frequentes com base nos documentos cadastrados pela profissional (RAG) | BOT-04 |
| RF03 | O sistema não deve informar valores de sessão de forma direta/imediata quando perguntado | BOT-05 |
| RF04 | O sistema deve classificar cada mensagem recebida em três níveis: normal, sofrimento intenso (atenção humana) ou emergência (risco à vida) | BOT-06, BOT-07 |
| RF05 | Ao classificar como emergência, o sistema deve interromper o fluxo normal da conversa e enviar a mensagem fixa de encaminhamento (SAMU 192, UPA/pronto-socorro, 190, CVV 188) | BOT-06, BOT-08 |
| RF06 | O sistema não deve prometer, na mensagem de emergência, que a profissional vai assumir a conversa ou responder imediatamente | BOT-06 |
| RF07 | Ao classificar como sofrimento intenso, o sistema deve marcar a conversa para revisão humana sem interromper o atendimento normal | BOT-07 |
| RF08 | O sistema deve permitir que a conversa volte ao fluxo normal (agendamento, dúvidas) após um episódio de risco, caso a pessoa retorne sem sinais de risco | BOT-08 |
| RF09 | O sistema deve notificar a profissional imediatamente quando um alerta de emergência for disparado | WEB-06 |
| RF10 | O sistema deve dar acesso à conversa completa (ou link direto) a partir do alerta | WEB-04 |
| RF11 | A profissional deve poder marcar um alerta como revisado | WEB-04 |
| RF12 | A profissional deve poder configurar o tom de voz e as mensagens padrão do assistente | WEB-01 |
| RF13 | A profissional deve poder fazer upload, visualizar e remover documentos da base de conhecimento | WEB-02 |
| RF14 | A profissional deve poder visualizar o histórico de conversas por canal | WEB-03 |
| RF15 | Cada profissional deve ter sua base de conhecimento e configuração isoladas das demais (multi-tenant) | Arquitetura geral |
| RF16 | O conteúdo das mensagens deve ser armazenado de forma criptografada | Já implementado |
| RF17 | O histórico de conversas de leads que não converteram deve ser excluído/anonimizado após 90 dias | Já implementado (retenção configurável) |

### Requisitos não funcionais

| RNF | Descrição |
|---|---|
| RNF01 | Em caso de dúvida na classificação de risco, o sistema deve favorecer falso positivo sobre falso negativo — mas **somente** dentro da categoria emergência (morte/suicídio/automutilação/perigo imediato); linguagem genérica de sofrimento (“preciso de ajuda”, “estou desesperada”) não deve, isoladamente, disparar o nível de emergência |
| RNF02 | O sistema nunca deve tentar diagnosticar ou dar aconselhamento clínico |
| RNF03 | A resposta a uma mensagem recebida deve ser rápida o suficiente para não gerar percepção de demora (esse é o maior ponto de perda de conversão já identificado) |
| RNF04 | Nenhum endpoint deve ter `professional_id` fixo no código — sempre parametrizado |
| RNF05 | O sistema deve ser auditável: alertas de segurança não devem ser editáveis/apagáveis pela profissional, apenas marcáveis como revisados |
| RNF06 | O protocolo de segurança deve ser testado com os cenários simulados que a própria Marília listou (ver seção 7) antes de qualquer uso com paciente real |
| RNF07 | Textos de mensagens de emergência não devem ser alterados livremente pelo código sem nova aprovação clínica dela — são texto aprovado, não copy editorial |

---

## 6. Estado atual do código (o que já existe hoje)

Checado direto no repositório em 16/09/2026:

- ✅ Backend FastAPI multi-tenant (`professionals`, `documents`, `chat`) funcionando por `slug`
- ✅ RAG com ChromaDB, uma coleção por profissional
- ✅ Resposta real via Claude API (não é mais placeholder)
- ✅ Criptografia de mensagens em repouso (`EncryptedText` no `models.py`)
- ✅ Política de retenção de 90 dias (configurável, script manual de purge)
- ✅ Painel simples em React/Vite: editar tom de voz e gerenciar documentos por slug
- ❌ **Nenhum modelo de dados pra alerta de segurança ainda** (`SafetyAlert` não existe em `models.py`)
- ❌ Nenhuma lógica de triagem/classificação de risco implementada ainda
- ❌ Nenhum modelo de agendamento (`Appointment`) nem integração com Google Calendar
- ❌ Nenhum modelo de pagamento/PIX
- ❌ WhatsApp real ainda não em produção (número de teste EUA não envia pra números BR)
- ❌ Sem login — identificação só por slug (decisão consciente, ver `planejamento-projeto.md`)

---

## 7. Critérios de triagem já aprovados pela Marília (resumo operacional)

Isso não é mais uma decisão em aberto — é a especificação que o
código de triagem (RF04–RF08) deve seguir.

**Dispara nível emergência** (frases como, mas não limitado a):
"não quero mais viver", "quero morrer", "quero me matar", "vou acabar
com minha vida", "seria melhor se eu não existisse", "queria dormir e
não acordar", "estou pensando em me machucar", "tenho um plano pra me
matar", "já fiz algo pra me machucar", "não consigo garantir que vou
ficar em segurança", relato de ingestão de medicamento/substância pra
se ferir, relato de violência ou perigo imediato.

**NÃO dispara nível emergência isoladamente** (mas pode disparar nível
"sofrimento intenso"): "preciso de ajuda", "estou desesperada", "não
estou bem", "estou deprimida", "perdi meu chão", "não consigo
continuar assim" — linguagem comum no nicho dela (sofrimento
relacional pós-término, traição, etc.) e não deve virar alarme de
risco à vida sozinha.

**Mensagem fixa aprovada pra nível emergência:**

> "Sinto muito que você esteja passando por isso. Este WhatsApp não
> funciona como canal de emergência e não é monitorado 24 horas. Se
> você corre risco de se machucar ou não consegue se manter em
> segurança, ligue agora para o SAMU pelo 192 ou procure uma UPA ou
> pronto-socorro. Se houver violência ou perigo imediato, ligue para o
> 190. Você também pode ligar gratuitamente para o CVV pelo 188 para
> conversar com alguém neste momento. Se puder, entre em contato agora
> com uma pessoa de confiança e não permaneça sozinha. Não espere uma
> resposta por este canal para buscar ajuda imediata."

**Cenários de teste que ela pediu explicitamente** antes de confiar no
sistema (usar como base dos testes automatizados/manuais do módulo de
triagem):

1. "Preciso de ajuda" isolado
2. Pedido urgente depois de um término
3. Relato de não comer/não tomar banho/não sair de casa
4. Linguagem intensa/dramática sobre relacionamento (sem risco real)
5. Referência à morte com contexto ambíguo
6. Desejo explícito de morrer
7. Ideação suicida explícita
8. Automutilação
9. Plano ou tentativa em andamento
10. Violência ou perigo imediato
11. Casos de falso positivo e falso negativo do próprio sistema, revisados por ela

---

## 8. Pendências que não bloqueiam o MVP, mas precisam de decisão

| Item | Situação | Ação |
|---|---|---|
| Texto de aviso "você está falando com uma IA" | O código já implementa esse aviso automaticamente (roadmap item 4, já concluído), mas na entrevista ela disse **"ainda não tenho certeza, preciso pensar melhor"** | Conflito a resolver: ou o aviso atual já está bom e só falta ela aprovar o texto exato, ou o comportamento precisa mudar. Levar o texto atual do código pra ela revisar diretamente |
| Retenção diferenciada: lead que não converteu vs. paciente que virou cliente | Hoje a política é uniforme (90 dias pra tudo). Ela pediu política própria e diferente para quem efetivamente inicia atendimento | Não é MVP — mas vale desenhar o campo de "status" (lead/paciente) no modelo `Conversation` desde já pra não precisar migrar depois |
| Retenção de telefone/contato para marketing (público de anúncios, campanhas de WhatsApp) | Pedido novo dela, fora do escopo original | Tem implicação de LGPD (uso pra marketing exige base legal/consentimento próprio, separado do uso para atendimento) — não é algo pra implementar sem desenho de consentimento explícito. Fica registrado como trabalho futuro com essa ressalva |

---

## 9. Checklist para validar a ordem de prioridade com a profissional

Perguntas objetivas pra confirmar com a Marília antes de travar o MVP
(pode ser um formulário curto ou conversa de 15 min):

1. Confirma que a ordem de valor pra ela é: **(1) nunca perder um caso
   de risco → (2) responder rápido pra não perder lead → (3)
   agendamento dentro da conversa → (4) pagamento automatizado**? Ou
   inverteria algo?
2. O texto de aviso de IA do sistema atual (pedir pra ela ler) — serve
   como está, ou ela quer mudar alguma coisa antes de aprovar?
3. Ela concorda em revisar os 11 cenários de teste da seção 7 assim
   que o módulo de triagem estiver pronto, antes de qualquer uso real?
4. Pra ela, tudo bem que o MVP rode com **canal simulado** (chat web)
   em vez de WhatsApp real na defesa, dado que o WhatsApp de produção
   ainda depende de um número brasileiro verificado?

---

## 10. Definição do MVP

> **Atualização (20/09/2026):** esta definição foi ampliada. O MVP com
> entrega em 09/10 passa a incluir WhatsApp, login mínimo e
> pré-agendamento no Google Calendar, e o item "Fica fora do MVP" abaixo
> vale só para o que não foi listado no plano. A definição vigente, o
> cronograma semanal e os riscos estão em `planejamento-mvp-9out.md`. Os
> critérios de triagem da seção 7 continuam valendo sem mudança.

**Entra no MVP** (tudo 🔴 P0 das seções 2 e 3):

- Chat funcional multi-tenant com RAG (já existe)
- Apresentação da profissional + resposta cuidadosa sobre preço
- Triagem de segurança em dois níveis (emergência + sofrimento
  intenso), com os critérios e o texto já aprovados na seção 7
- Interrupção de fluxo após emergência, com retomada possível depois
- Painel web: configuração do assistente, base de conhecimento
  (já existem) + inbox de conversas + tela de alertas de segurança
  com marcação "revisado" + marcação "necessita atenção da Marília"
- Canal: simulado (chat web), suficiente pra demonstrar o conceito na
  defesa

**Fica fora do MVP** (🟡 P1 e 🟢 P2):

- WhatsApp em produção, Instagram, TikTok
- Google Calendar / pré-agendamento
- Validação de PIX por visão computacional
- Dashboard de métricas
- Notificação por WhatsApp real do alerta (MVP usa notificação dentro
  do painel)
- Login/cadastro completo, cobrança/assinatura, onboarding
  self-service do WhatsApp (já declarados trabalho futuro)
- Mobile companion
- Follow-up automático de leads parados

**Próximo passo prático**: com os critérios da seção 7 aprovados, o
maior bloqueio do roadmap (`planejamento-projeto.md`, item 2) está
resolvido — dá pra ir direto pro item 3 (construir a triagem) em
paralelo com o inbox de conversas e a tela de alertas no painel.
