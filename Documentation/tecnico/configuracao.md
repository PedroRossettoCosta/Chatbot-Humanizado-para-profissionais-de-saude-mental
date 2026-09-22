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
| `CHROMA_PERSIST_DIR` | não | Pasta onde o ChromaDB guarda os vetores |
| `FRONTEND_URL` | não | Origem liberada no CORS. Precisa bater com a porta do Vite |
| `DATA_ENCRYPTION_KEY` | sim | Cifra os dados sensíveis em repouso |
| `DATA_RETENTION_DAYS` | não | Dias até uma conversa inativa ser apagada. Padrão: 90 |
| `WHATSAPP_ACCESS_TOKEN` | só com WhatsApp | Token permanente do usuário de sistema da Meta |

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
| `VITE_API_URL` | Endereço da API. Padrão: `http://127.0.0.1:8000` |

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

## 5. Onde cada segredo fica

| Segredo | Onde | Versionado? |
|---|---|---|
| Chaves de API e tokens | `backend/.env` | Não |
| Chave da conta de serviço do Google | `backend/secrets/*.json` | Não |
| Valores de exemplo, em branco | `backend/.env.example` | Sim |

Em produção, o `.env` é criado direto no servidor, com permissão de
leitura restrita ao usuário do serviço, e nunca chega lá pelo
repositório.
