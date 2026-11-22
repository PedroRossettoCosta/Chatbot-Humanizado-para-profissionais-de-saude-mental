# Mapa do caminho dos dados

Escrito em 21/11/2026 (item 10 do feedback do orientador). Para cada
serviço externo: que dados recebe, para quê, onde fica, por quanto tempo
e quem pode acessar o conteúdo.

- **O que vem do código** foi conferido em `backend/app/services/`
  (`pipeline.py`, `llm.py`, `triage.py`, `notifications.py`,
  `calendar.py`) e em `frontend/vercel.json`.
- **Local e prazo** vêm da documentação pública de cada serviço,
  consultada em 21/11/2026 (fontes no fim). O que a documentação não diz
  está marcado como "não confirmado".

Proteções internas (cifra no banco, retenção, logs sem conteúdo) estão em
[seguranca-lgpd.md](tecnico/seguranca-lgpd.md); as ameaças, em
[modelo-de-ameacas.md](modelo-de-ameacas.md).

## O que a Anthropic recebe

A Anthropic recebe dados em duas chamadas diferentes. **Nenhuma das duas
leva o telefone nem o nome de perfil do WhatsApp do contato.** O nome só
vai se a própria pessoa o escrever na conversa.

### Triagem (camada 2, modelo `claude-opus-5`): quase toda mensagem de texto

**Quando a chamada é feita.** Toda mensagem de texto que o contato
manda passa pela triagem antes de qualquer resposta. Isso vale mesmo com
a profissional no controle da conversa ou com a conversa em espera de
emergência. Só três casos não chegam à Anthropic:

- a camada 1 (regras fixas, no servidor) já deu emergência: o modelo não
  é chamado;
- o contato passou de 50 mensagens na última hora: só a camada 1 roda;
- áudio, foto e documento: não passam pela triagem nem vão para o modelo.

**O que vai em cada chamada:**

- as instruções fixas da triagem;
- a descrição de especialidade e público escrita pela profissional;
- **as até 3 mensagens mais recentes da conversa dos últimos 5 minutos**,
  da pessoa, da SelenIA e da profissional, incluindo a mensagem nova. Ficam de fora a
  mensagem de risco e o texto de emergência já tratados.

**O que volta:** o nível (normal, sofrimento intenso, dúvida, emergência)
e uma justificativa curta. A justificativa não é gravada no banco.

### Resposta (modelo `claude-sonnet-5`): só quando a SelenIA responde

**Quando a chamada é feita.** Só quando a triagem não deu emergência, a
pessoa não pediu a profissional e a conversa está com a SelenIA.

**O que vai em cada chamada:**

- **Instruções e perfil:** papel e limites, lista do "nunca dizer", nome
  e pronomes da profissional, especialidade e público, valores e
  funcionamento, duração da sessão, tom de voz e exemplos de resposta.
- **Documentos:** até 4 trechos dos documentos da base de conhecimento
  da profissional.
- **Agenda, quando o assunto é horário e a agenda está conectada:**
  horários livres (calculados no servidor, sem os compromissos dela) e
  as sessões e os pedidos **do próprio contato**. Se ela estiver "em
  consulta", vai só "em atendimento até HH:MM", sem o que ela está
  fazendo.
- **Histórico:** as **últimas 12 mensagens da conversa**, da pessoa, da
  SelenIA e da profissional. A mensagem de risco e o texto de emergência
  com mais de 5 minutos ficam de fora.
- **Resultados das ferramentas:** lista de horários, resultado do pedido
  de horário, pedido levado à profissional.

**O que volta:** o texto da resposta e, quando for o caso, pedidos de
ferramenta. O servidor confere cada pedido de ferramenta antes de agir.

**Retenção na Anthropic** (vale para as duas chamadas):

- pela central de privacidade, entradas e saídas da API são apagadas em
  até **30 dias**, salvo acordo diferente ou conteúdo marcado por
  violação da política de uso, que pode ficar por até 2 anos;
- a API não usa os dados para treinar modelos sem opt-in;
- não há acordo de retenção zero nem região contratada.

## Tabela por serviço

| Serviço | Que dados recebe | Para quê | Onde fica | Por quanto tempo | Quem pode acessar o conteúdo |
|---|---|---|---|---|---|
| **Anthropic** (API da Claude) | Triagem: até 3 mensagens recentes e o público da profissional, em quase toda mensagem de texto. Resposta: perfil, trechos dos documentos, horários livres e sessões do próprio contato, últimas 12 mensagens. Sem telefone nem nome de perfil (detalhes acima) | Classificar o risco e escrever a resposta | Fora do Brasil. Empresa dos EUA; país do processamento **não confirmado**, sem região contratada | Até 30 dias, ou até 2 anos se o conteúdo for marcado por violação da política de uso | Anthropic, para operar o serviço e para segurança (política de uso). No projeto, quem tem a chave de API só vê custo e uso, não o conteúdo |
| **Meta / WhatsApp** (Cloud API) | Todas as mensagens nos dois sentidos (texto, áudio, foto, documento), o número do contato, o nome de perfil, o número da profissional e os status de entrega | Entregar e receber as mensagens | Data centers da Meta (América do Norte e União Europeia, pela documentação). Armazenamento local no Brasil não contratado | Mensagens: no máximo 30 dias na Cloud API. Mídia: cerca de 30 dias, depois o painel não consegue mais abrir. O webhook tenta reentregar por até 7 dias | Meta, como operadora. O app do WhatsApp do contato guarda a conversa do lado dele por tempo indeterminado |
| **Google** (Agenda, Meet e login) | Login: e-mail, nome, foto e id do Google da profissional. Agenda: consultas de livre/ocupado; eventos criados pela SelenIA com o **nome dado na conversa e o telefone do contato**; link do Meet da sessão confirmada | Login no painel, horários livres, reservar e confirmar sessão | Conta Google da profissional. País **não confirmado** (Google não fixa região para conta pessoal) | Enquanto o evento estiver na agenda dela: **fora da retenção de 90 dias da SelenIA**. Desconectar a agenda apaga o token, não os eventos | A profissional e quem tiver acesso à agenda dela; o Google, como provedor |
| **Brevo** (e-mail) | Endereço de alerta da profissional, assunto e corpo: tipo do aviso, data e hora, canal e link do painel. **Sem conteúdo de conversa e sem dado do contato** | Avisar a profissional de alerta, pedido para falar com ela e pedido de horário | União Europeia (OVH na França e na Alemanha; Google Cloud na Bélgica, pela documentação da Brevo) | Registro do envio na Brevo: prazo **não confirmado**. O e-mail fica na caixa da profissional | Brevo; a profissional na caixa dela; o administrador da conta Brevo (Pedro) vê os registros de envio |
| **Railway** (servidor e banco) | Tudo o que o backend processa: mensagens, alertas, agenda, documentos e perfis. No Postgres, conteúdo, telefone, nome de perfil, trecho do alerta, token do Google e nome do paciente ficam cifrados. Os trechos dos documentos no ChromaDB (volume) ficam sem cifra. A chave de cifra fica numa variável de ambiente do mesmo projeto | Rodar o backend, o banco e a base vetorial | Região do projeto **não confirmada** (o CLI mostra a região padrão, sem valor explícito; conferir no painel do Railway) | Conversas: até 90 dias sem atividade, pelo script de retenção, que hoje é **manual**. Documentos e perfil: até a profissional apagar | Railway, como provedor. Quem administra o projeto (Pedro) tem o banco e a chave, então consegue decifrar |
| **Vercel** (painel) | Os arquivos do painel. Todas as chamadas do painel ao backend (`/api/*`) passam pela Vercel antes de chegar ao Railway: conversas decifradas, alertas, agenda e o cookie de sessão, em trânsito | Servir o painel e encaminhar as chamadas ao backend | Rede global da Vercel (borda mais próxima de quem acessa) | Corpo das requisições: não é guardado pela Vercel, pela documentação. Logs de execução e de origens externas, com caminho e status: cerca de 1 hora no plano gratuito | Vercel, como provedor, em trânsito. Quem administra o projeto (Pedro) vê os logs, sem corpo |

## Pontos para o texto

- **A Anthropic recebe trechos de quase toda mensagem de texto**, não só
  das que geram resposta, porque a triagem roda antes de tudo. Isso inclui
  conversas que a profissional assumiu.
- **O Google Agenda guarda nome e telefone fora da retenção** da SelenIA
  (decisão de 28/09/2026). Precisa constar na política de privacidade.
- **A Meta tem todo o conteúdo** por até 30 dias; é inerente ao canal.
- **Brevo e e-mail não levam conteúdo** de conversa nem dado do contato.
- **A Vercel vê tudo em trânsito** porque faz o papel de proxy do painel;
  o painel poderia chamar o Railway direto, mas isso exigiria outra
  configuração de cookie e de CORS.
- A política de retenção de 90 dias **só vale para o banco da SelenIA**;
  os outros prazos são os de cada serviço.

## Fontes (consultadas em 21/11/2026)

- Anthropic, por quanto tempo os dados da API comercial são guardados:
  <https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-commercial-api-data>
- Meta, privacidade e segurança dos dados da Cloud API:
  <https://developers.facebook.com/documentation/business-messaging/whatsapp/data-privacy-and-security>;
  armazenamento local:
  <https://developers.facebook.com/documentation/business-messaging/whatsapp/local-storage/>
- Brevo, local de armazenamento:
  <https://help.brevo.com/hc/en-us/articles/360001005510-Data-storage-location>
- Vercel, logs de execução e limites:
  <https://vercel.com/docs/logs/runtime>,
  <https://vercel.com/docs/observability/limits-and-pricing>
