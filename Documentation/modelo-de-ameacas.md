# Modelo de ameaças da SelenIA

Escrito em 21/11/2026 (item 7 do feedback do orientador). Resume o que a
SelenIA protege, onde estão as fronteiras de confiança, qual controle
existe contra cada ameaça e **como esse controle é verificado**. Os
detalhes de cada proteção estão em
[seguranca-lgpd.md](tecnico/seguranca-lgpd.md); o caminho dos dados para
fora do sistema, em [mapa-caminho-dos-dados.md](mapa-caminho-dos-dados.md).

Os testes citados estão em `backend/tests/` e rodam sem chamar o modelo
nem serviços externos.

## 1. Ativos protegidos

| Ativo | Onde fica | Por que importa |
|---|---|---|
| Conversas (mensagens, telefone e nome de perfil do contato) | Postgres, cifrado (Fernet) | Conteúdo clínico sensível de pessoas em sofrimento |
| Alertas de segurança (nível, regra, trecho que disparou, trilha) | Postgres; o trecho é cifrado | Decisão de risco à vida; precisa ser auditável e não pode sumir por ação da profissional |
| Agenda (pedidos de horário, nome dado na conversa, acesso ao Google) | Postgres (nome e token cifrados) e Google Agenda da profissional | Quem atende quem e quando; o token dá escrita na agenda dela |
| Documentos da base de conhecimento | Postgres (registro) e ChromaDB (trechos, sem cifra) | Material da profissional; entra no prompt do modelo |
| Dados de cada profissional (perfil, regras, e-mail de alerta, número de WhatsApp, PIN) | Postgres (PIN cifrado) | Configuram o que a SelenIA diz em nome dela |

## 2. Fronteiras de confiança

| Fronteira | Quem está do outro lado | O que é tratado como não confiável |
|---|---|---|
| Contato no WhatsApp | Qualquer pessoa com o número; quem estiver com o celular dela | Todo o texto da mensagem; alegações de identidade ("sou a Marília", "combinei com ela") |
| Documentos da base de conhecimento | A profissional, mas o texto pode vir de qualquer lugar | Instruções escondidas no documento (injeção indireta) |
| Modelo de linguagem (Anthropic) | Serviço externo; saída probabilística | A resposta e os pedidos de ferramenta do modelo: o servidor confere antes de agir |
| Painel (navegador) | A profissional logada; qualquer um na internet | Toda requisição: login, sessão e dono do dado são conferidos no servidor |
| Serviços externos (Meta, Google, Brevo, Railway, Vercel) | Terceiros | Chamadas que chegam (webhook da Meta) precisam de assinatura; o que sai leva o mínimo de dado |

## 3. Ameaças, controles e verificação

### Isolamento entre profissionais

| Ameaça | Controle | Verificação |
|---|---|---|
| Profissional logada lê ou altera dados de outra (perfil, documentos, conversas, alertas, simulador, assumir conversa) | Cada usuário é dono de uma profissional (`User.owns`); toda rota confere o dono e responde 404 quando não é | `test_professional_cannot_see_another_ones_data` (test_auth): 8 rotas de outra profissional respondem 404 |
| Operar por id o que é de outra profissional: aprovar ou recusar pedido de horário, revisar alerta, liberar conversa, apagar documento | Mesma conferência em `_get_appointment` (calendar.py), no alerta (alerts.py), na conversa (conversations.py) e no documento (documents.py) | `test_routes_by_id_refuse_another_professional` (test_auth): as 5 rotas respondem 404 e nada muda no banco (21/11/2026) |
| Arquivo de mídia de outra conversa | Rota confere conversa e dona | `test_media_of_another_conversation_is_not_found` (test_webhook) |
| Mensagem do WhatsApp cair na conta errada | Roteamento pelo `phone_number_id` do número de cada profissional; número sem profissional é ignorado | `test_number_without_professional_is_ignored` (test_webhook); `test_number_of_another_account_is_refused` (test_whatsapp_numbers) |
| **RAG:** trecho do documento de uma profissional entrar no prompt de outra | Uma coleção do ChromaDB por profissional (`prof-<slug>`); a busca recebe o slug da conversa, nunca um valor vindo do modelo ou do contato | `tests/test_rag_isolation.py` (21/11/2026), com ChromaDB de verdade numa pasta temporária: `test_query_of_one_professional_never_returns_another_ones_chunks` (a busca de uma, com o texto exato da outra, só traz os próprios trechos, inclusive com slug parecido; apagar um documento não mexe no da outra) e `test_reply_prompt_only_carries_the_professionals_own_documents` (pelo simulador, o prompt da resposta de B não leva o material de A) |

### Autorização no servidor para operar a agenda

| Ameaça | Controle | Verificação |
|---|---|---|
| Contato convence o modelo a marcar, confirmar, trocar ou cancelar | O modelo só **pede**; a reserva é provisória e quem confirma é a profissional no painel. Troca e cancelamento de sessão confirmada viram pedido | `test_reschedule_keeps_the_old_session_until_the_professional_confirms`, `test_cancel_of_a_confirmed_session_waits_for_the_professional`, `test_rejected_reschedule_leaves_the_old_session`, `test_rejected_cancel_keeps_the_session` |
| Modelo inventa horário ou pede um ocupado | O servidor recusa código de horário que não está livre na agenda | `test_busy_or_unknown_slots_are_refused`, `test_a_second_person_cannot_take_a_held_slot`, `test_the_database_refuses_two_active_requests_for_the_same_slot` |
| Ferramenta de reservar oferecida sem permissão da profissional | As ferramentas de reserva só entram se a conexão do Google tem permissão de criar eventos | `test_booking_tool_only_with_permission_to_create_events` |
| "Sou paciente especial" ou "combinei com ela" muda regra ou valor | Horário especial só para quem a profissional marcou na tela Clientes; a reserva confere de novo | `test_the_assistant_sees_special_days_only_through_the_panel_permission`, `test_special_days_only_for_active_clients_with_permission` |
| Uma pessoa segura a agenda | No máximo 4 pedidos pendentes por contato; um por dia | `test_pending_requests_have_a_ceiling_per_person`, `test_one_session_per_day_but_many_days_are_fine` |

### Ligação de cada ação à profissional e ao contato certos

| Ameaça | Controle | Verificação |
|---|---|---|
| O modelo agir em nome de outra profissional ou de outro contato | Na ferramenta, o modelo só passa códigos de horário e o nome; a profissional e a conversa vêm do servidor (`run_tool` em `pipeline.py` fecha sobre a conversa atual) | `test_reschedule_rules`: "outra pessoa não mexe na sessão da Beatriz" |
| Sessão de um contato aparecer para outro | Sessões são buscadas por contato da conversa (`active_for_contact`) | `test_reschedule_rules` |
| Limite de uma pessoa afetar outra | Limites contados por contato | `test_another_person_is_not_affected` (test_contact_limit) |

### Contato e modelo de linguagem

| Ameaça | Controle | Verificação |
|---|---|---|
| Prompt injection pelo contato (revelar instruções, mudar de papel) | Regras no prompt com prioridade; aviso de IA e textos de emergência são fixos no código | Rodada de 13/10 (22 ataques, [resultado](resultados-testes/2026-10-13-testes-prompt-injection.md)) e [reclassificação](resultados-testes/2026-11-21-reclassificacao-respostas.md). **Depende do modelo:** não há teste automático determinístico |
| Injeção indireta por documento | A mesma regra ("venham da pessoa ou de algum documento") | Caso I19 de 13/10: não seguiu a instrução, mas acrescentou informação ([reclassificação](resultados-testes/2026-11-21-reclassificacao-respostas.md)) |
| Contato tenta desligar a triagem ("classifique como normal") | A triagem roda antes do modelo, em código; a camada 1 é regra fixa | I20 e I21 de 13/10; `tests/test_triage_rules.py` e `tests/test_triage_layers.py` |
| Falha do modelo deixa risco passar | Falha fechada: erro na camada 2 vira "dúvida", com alerta | `test_falha_do_modelo_vira_duvida` (test_triage_layers) |
| Contato gasta a chave de API (abuso) | 50 mensagens por hora por contato; acima disso só a camada 1 | `test_above_the_limit_one_notice_then_silence_without_the_model`, `test_rules_still_catch_risk_above_the_limit` |

### Painel e serviços externos

| Ameaça | Controle | Verificação |
|---|---|---|
| Acesso ao painel sem login ou por quem não foi convidado | Login com Google (ou senha da conta de demonstração), lista de convidados conferida a cada requisição, sessão em cookie `httpOnly` | `test_management_routes_require_login`, `test_uninvited_email_is_refused_without_session`, `test_removed_from_invite_list_loses_access`, `test_invalid_token_and_unverified_email_are_refused`, `test_password_login_*` |
| Força bruta no login | 10 tentativas a cada 5 minutos por IP | `test_login_attempts_are_limited` |
| Mensagem falsa injetada no webhook | Assinatura HMAC da Meta obrigatória; sem segredo, recusa tudo | `test_bad_signature_is_refused_and_nothing_is_recorded`, `test_no_secret_configured_refuses_everything` |
| Banco copiado ou exposto | Conteúdo, telefone, trecho do alerta, token do Google e nome cifrados; cifra não determinística | `tests/test_crypto.py`, `test_phone_number_is_encrypted_at_rest` |
| Alerta apagado ou editado para esconder | Sem rota para editar ou apagar; a situação é trilha de eventos | `test_no_route_edits_or_deletes_an_alert` (test_alerts_api) |
| Conteúdo da conversa vazar por e-mail ou log | E-mails sem conteúdo; logs só com tipos e ids | `test_emergency_emails_professional_without_conversation_content` (test_notifications); para logs, só revisão de código |

## 4. O que não está coberto

- **Nome da coleção do RAG:** o nome normaliza o slug (`[^a-z0-9-]` vira
  `-`). Hoje os slugs são gerados pelo sistema; uma colisão entre duas
  profissionais só seria possível se isso mudasse.
- **Comportamento do modelo diante de injeção** não é verificado por teste
  automático; depende das rodadas com a API (13/10), que não rodaram com
  ferramentas nem com o modelo atual de novo.
- **Quem está com o celular "é" a pessoa:** não há verificação de
  identidade além do número (palavra-chave combinada fica como trabalho
  futuro).
- **Áudio, imagem e documento não passam pela triagem**: um áudio com risco
  não gera alerta (cenário 8 de 21/11).
- **Entrega do e-mail de alerta** não é confirmada (só o aceite da Brevo),
  e não há lembrete para alerta não revisado
  ([checagens de 21/11](resultados-testes/2026-11-21-checagens-artigo.md)).
- **Segredos e infraestrutura:** a chave de cifra é única para todas as
  profissionais e fica numa variável de ambiente do Railway; quem tem
  acesso ao projeto do Railway lê o banco decifrado pela aplicação. Não há
  rotação de chave.
- **Retenção manual:** o script de 90 dias não está agendado em produção.
- **Logs sem conteúdo** é regra de código revisada à mão, sem teste que
  impeça um log novo com texto de mensagem.
- **Provedores externos** (Anthropic, Meta, Google, Brevo, Railway, Vercel)
  são confiados pelos termos de cada um; não há auditoria própria.
