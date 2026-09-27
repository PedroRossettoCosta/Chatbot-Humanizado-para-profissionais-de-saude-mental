# Configuração

Variáveis de ambiente e as integrações externas (Google, Meta).

> **Nenhum segredo vai para o Git.** O `.env` e a pasta
> `backend/secrets/` estão no `.gitignore`. O que é versionado é o
> `.env.example`, sempre com os valores em branco.

---

## 1. Variáveis do backend (`backend/.env`)

| Variável | Obrigatória | Para que serve |
|---|---|---|
| `DATABASE_URL` | sim | Conexão com o PostgreSQL. O padrão já aponta para o contêiner local |
| `ANTHROPIC_API_KEY` | sim | Chave da API da Claude, que gera as respostas |
| `CLAUDE_MODEL` | não | Modelo usado. Padrão: `claude-sonnet-5` |
| `TRIAGE_MODEL` | não | Modelo da camada 2 da triagem, separado de propósito. Padrão: `claude-opus-5` |
| `TRIAGE_TIMEOUT_SECONDS` | não | Tempo máximo da camada 2 antes de tratar como falha (dúvida). Padrão: 20 |
| `CHROMA_PERSIST_DIR` | não | Pasta onde o ChromaDB guarda os vetores |
| `FRONTEND_URL` | não | Origem liberada no CORS. Precisa bater com a porta do Vite |
| `DATA_ENCRYPTION_KEY` | sim | Cifra os dados sensíveis em repouso |
| `DATA_RETENTION_DAYS` | não | Dias até uma conversa inativa ser apagada. Padrão: 90 |
| `WHATSAPP_ACCESS_TOKEN` | só com WhatsApp | Token permanente do usuário de sistema da Meta |
| `WHATSAPP_APP_SECRET` | só com WhatsApp | Segredo do app (Configurações do app → Básico). Confere a assinatura de cada chamada do webhook; vazio = nada entra |
| `WHATSAPP_VERIFY_TOKEN` | só com WhatsApp | Senha do desafio da Meta ao cadastrar o webhook. Qualquer texto longo; o mesmo vai no painel da Meta |
| `WHATSAPP_API_VERSION` | não | Versão da Graph API. Padrão: `v25.0` |
| `PUBLIC_WEBHOOK_HOST` | com túnel | Endereço público do túnel, sem `https://` (ex.: `algo.ngrok-free.dev`). Por ele só passa `/webhook/`. O `iniciar.bat` usa para abrir o ngrok |
| `REPLY_DEBOUNCE_SECONDS` | não | Espera antes de responder no WhatsApp, para juntar mensagens quebradas. Padrão: 6 |
| `SMTP_HOST` | para enviar alertas | Servidor de e-mail. Sem ele, o alerta registra `notify_failed` ([alerta por e-mail](../funcionalidades/alerta-por-email.md)) |
| `SMTP_PORT` | não | Padrão: 587 (STARTTLS) |
| `SMTP_USER` / `SMTP_PASSWORD` | para enviar alertas | Conta que envia. No Gmail, use uma **senha de app**, nunca a senha da conta |
| `SMTP_FROM` | não | Remetente exibido. Padrão: o `SMTP_USER` |
| `GOOGLE_CLIENT_ID` | para o login | Client ID "Web application" do Google Cloud ([login com Google](../funcionalidades/login-com-google.md)). Não é segredo |
| `ALLOWED_EMAILS` | para o login | E-mails convidados, separados por vírgula. Vazio = ninguém entra |
| `SESSION_DAYS` | não | Validade da sessão do painel. Padrão: 7 |
| `SESSION_COOKIE_SECURE` | em produção | `true` com HTTPS. Padrão: `false` (desenvolvimento em http) |

Para declarar uma variável nova, adicione o campo em
`app/config.py` **e** a linha correspondente no `.env.example`. Se a
variável existir só no `.env`, a aplicação recusa subir.

### Gerando as chaves

`DATA_ENCRYPTION_KEY` (com o venv ativado, dentro de `backend/`):

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Trocar essa chave torna ilegível tudo que já foi cifrado**: mensagens
e contatos gravados antes deixam de ser recuperáveis. Se um dia for
preciso rotacionar, o caminho é decifrar com a chave antiga e cifrar com
a nova, em uma migração própria.

`ANTHROPIC_API_KEY`: gerada em
[console.anthropic.com](https://console.anthropic.com). O modelo é
pré-pago, sem mensalidade.

## 2. Variáveis do front-end (`frontend/.env`)

| Variável | Para que serve |
|---|---|
| `VITE_API_URL` | Endereço da API visto pelo navegador. Padrão: `/api`, no mesmo endereço do painel (senão o cookie do login não vai junto) |
| `VITE_API_TARGET` | Para onde o proxy do Vite repassa `/api`. Padrão: `http://127.0.0.1:8000` |

## 3. Google Calendar

Usado para consultar disponibilidade e criar pré-agendamentos.

A autenticação é por **conta de serviço**: uma identidade que pertence à
aplicação, não a uma pessoa. A profissional compartilha a agenda dela
com o e-mail dessa conta, como faria com um colega.

A alternativa seria o login com Google de cada profissional (OAuth).
Isso será necessário quando o produto for aberto para muitas
profissionais, mas exige passar pela verificação do Google e lidar com
um token que expira. Para o MVP, a conta de serviço entrega o mesmo
resultado sem nada disso.

### Configuração, uma vez por projeto

1. Em [console.cloud.google.com](https://console.cloud.google.com), crie
   um projeto. Não é preciso ativar faturamento.
2. Em **APIs e serviços → Biblioteca**, ative a **Google Calendar API**.
3. Em **IAM e administrador → Contas de serviço**, crie uma conta. Não
   precisa atribuir papéis.
4. Nela, aba **Chaves → Adicionar chave → JSON**. O arquivo é baixado.
5. Mova o arquivo para `backend/secrets/` (pasta ignorada pelo Git).
6. Copie o e-mail da conta de serviço, algo como
   `nome@projeto.iam.gserviceaccount.com`.

### Configuração, uma vez por profissional

No Google Agenda dela:

1. Crie uma agenda dedicada (ex.: "Atendimentos"), para não expor a
   agenda pessoal inteira.
2. Nas configurações dessa agenda, em **Compartilhar com pessoas
   específicas**, adicione o e-mail da conta de serviço com a permissão
   **"Fazer alterações (ver eventos privados como livre/ocupado)"**.
3. Em **Integrar agenda**, copie o **ID da agenda** e guarde no campo
   `calendar_id` da profissional.

A permissão escolhida é deliberada: permite criar e editar eventos, mas
mostra os compromissos existentes apenas como "ocupado", sem título.
Para calcular disponibilidade isso basta, e o conteúdo clínico da agenda
não é exposto ao sistema.

## 4. WhatsApp (Meta Cloud API)

### Conceitos

| Termo | O que é |
|---|---|
| App | O aplicativo criado no Meta for Developers |
| Conta do WhatsApp (WABA) | O contêiner que agrupa números |
| Número | A linha que envia e recebe, registrada na API |
| Usuário de sistema | Identidade não-humana, dona do token permanente |
| Template | Mensagem pré-aprovada, exigida fora da janela de 24h |

### Passos

1. Crie o app no [Meta for Developers](https://developers.facebook.com)
   e adicione o produto WhatsApp.
2. Em **Business Settings → Usuários → Usuários do sistema**, crie um
   usuário com acesso de administrador.
3. Atribua a ele o **app** e a **conta do WhatsApp**, ambos com controle
   total.
4. Clique em **Gerar token**, escolha validade **Nunca** e marque
   `whatsapp_business_management` e `whatsapp_business_messaging`. O
   token aparece uma única vez — guarde em `WHATSAPP_ACCESS_TOKEN`.
5. Registre o número: **Contas do WhatsApp → Phone numbers → Adicionar
   telefone**. Escolha o nome de exibição, a categoria, e verifique por
   SMS ou ligação.

### Pontos de atenção

- **O número precisa ser brasileiro.** Desde setembro de 2025 a Meta
  restringe mensagens entre países envolvendo o Brasil, então o número
  de teste americano não fala com números brasileiros.
- **O número sai do app comum.** Depois de registrado na Cloud API, a
  linha deixa de funcionar no WhatsApp normal do celular. Use um chip
  dedicado.
- **O nome de exibição passa por revisão**, que leva de horas a alguns
  dias. Enquanto isso o número já recebe mensagens.
- **A janela de 24h:** fora de 24h desde a última mensagem do contato,
  só é possível enviar template aprovado.
- **Número por profissional:** o "phone number ID" do número vai em
  `professionals.whatsapp_phone_number_id`; é por ele que o webhook
  sabe de quem é a mensagem.
- **App publicado:** enquanto o app estiver em desenvolvimento, a Meta
  só entrega os testes do painel, não mensagens reais.

### Webhook e túnel

1. Conta gratuita no [ngrok](https://ngrok.com), com o domínio fixo de
   desenvolvimento (**Domains**) e o authtoken instalado:
   `ngrok config add-authtoken ...`.
2. `PUBLIC_WEBHOOK_HOST` com esse domínio, `WHATSAPP_APP_SECRET` e
   `WHATSAPP_VERIFY_TOKEN` no `backend/.env`.
3. `iniciar.bat` abre o túnel (`ngrok http --domain=... 8000`).
4. Na Meta, caso de uso do WhatsApp → Configuração da produção →
   **Configurar webhooks**: callback `https://{PUBLIC_WEBHOOK_HOST}/webhook/whatsapp`
   e o verify token → **Verificar e salvar** → ligar **Assinar
   webhooks** da conta. Em Webhooks → Whatsapp Business Account, o
   campo **messages** precisa estar assinado.

## 5. Onde cada segredo fica

| Segredo | Onde | Versionado? |
|---|---|---|
| Chaves de API, tokens, App Secret da Meta e senha do e-mail de envio | `backend/.env` | Não |
| Authtoken do ngrok | configuração do ngrok no usuário do Windows | Não |
| Chave da conta de serviço do Google | `backend/secrets/*.json` | Não |
| Valores de exemplo, em branco | `backend/.env.example` | Sim |

Em produção, o `.env` é criado direto no servidor, com permissão de
leitura restrita ao usuário do serviço, e nunca chega lá pelo
repositório.
