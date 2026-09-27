# Arquitetura

Como o MarIA é organizado por dentro e por que cada decisão foi tomada.
Para o contexto de produto e as decisões combinadas com a profissional,
veja [planejamento-projeto.md](../planejamento-projeto.md).

---

## 1. Peças do sistema

| Peça | Tecnologia | Papel |
|---|---|---|
| API | Python + FastAPI | Núcleo: recebe mensagens, decide o que fazer, responde |
| Banco relacional | PostgreSQL (Docker) | Conversas, contatos, alertas, agendamentos |
| Banco vetorial | ChromaDB (local) | Documentos da profissional, para o RAG |
| Modelo de linguagem | API da Claude | Gera a resposta, no tom de voz configurado |
| Painel | React + Vite | Onde a profissional configura e acompanha |
| Agenda | Google Calendar API | Disponibilidade e pré-agendamento |
| Canal | WhatsApp Cloud API | Onde o paciente realmente escreve |

O PostgreSQL roda em contêiner só no ambiente de desenvolvimento. Nada
no código depende disso: a aplicação só conhece a URL do banco.

## 2. O caminho de uma mensagem

```
Paciente escreve
       │
       ▼
┌─────────────────┐   O canal traduz o formato de origem
│  Camada de      │   (payload da Meta, ou JSON do simulador)
│  canal          │   para o vocabulário interno do sistema.
└────────┬────────┘
         ▼
┌─────────────────┐   Identifica o contato pelo telefone ou pela
│  Contato e      │   sessão, encontra ou abre a conversa, grava
│  conversa       │   a mensagem recebida.
└────────┬────────┘
         ▼
┌─────────────────┐   Roda ANTES de qualquer outra coisa.
│  Triagem de     │   ├─ emergência → texto fixo aprovado + alerta,
│  segurança      │   │                e o fluxo normal para aqui
│                 │   ├─ dúvida → alerta e segue
│                 │   └─ sofrimento intenso → marca a conversa e segue
└────────┬────────┘
         ▼
┌─────────────────┐   Profissional no controle ou espera de
│  Handoff        │   emergência → silêncio. Pedido da profissional
│                 │   ou recusa do bot → texto fixo (ver
│                 │   funcionalidades/handoff-e-em-consulta.md)
└────────┬────────┘
         ▼
┌─────────────────┐   Busca os trechos mais parecidos com a pergunta
│  RAG            │   entre os documentos daquela profissional.
└────────┬────────┘
         ▼
┌─────────────────┐   Monta o prompt (papel, limites, tom de voz,
│  Geração da     │   trechos recuperados) e chama a Claude.
│  resposta       │
└────────┬────────┘
         ▼
   Resposta gravada e devolvida pelo mesmo canal
   (e, se houve alerta, e-mail para a profissional em segundo plano)
```

### Por que a triagem roda primeiro

Se a checagem de risco dependesse do modelo de linguagem decidir o que
fazer, o comportamento em uma emergência seria imprevisível. Colocando
a triagem como um portão na frente de tudo, o caminho de emergência é
fixo: um texto aprovado pela profissional, sempre igual, sem improviso
do modelo, e um alerta registrado.

É por isso também que a mensagem de emergência é uma constante no
código, e não algo gerado pela Claude.

## 3. As camadas do backend

```
app/
├── routers/     ← Fronteira HTTP. Recebe requisição, valida, responde.
│                  Não contém regra de negócio.
├── services/    ← Onde as regras vivem. Não sabe o que é HTTP.
├── models.py    ← As tabelas e como elas se ligam.
├── schemas.py   ← O formato de entrada e saída da API (Pydantic).
├── database.py  ← Conexão e sessão do banco.
└── config.py    ← Variáveis de ambiente.
```

A separação entre `routers` e `services` é o que permite testar as
regras sem subir a API, e reaproveitar a mesma regra em canais
diferentes. Exemplo concreto: `services/conversations.py` é chamado
hoje pelo simulador e será chamado amanhã pelo webhook do WhatsApp, sem
alteração.

### Os serviços

| Módulo | Responsabilidade |
|---|---|
| `conversations.py` | Encontrar ou criar contato e conversa, gravar mensagens, montar o histórico |
| `rag.py` | Falar com o ChromaDB: indexar e buscar trechos |
| `llm.py` | Montar o prompt de sistema e chamar a API da Claude |
| `text_extraction.py` | Extrair texto de PDF/DOCX/TXT e dividir em trechos |
| `crypto.py` | Cifrar dados sensíveis e gerar índice de busca |
| `triage.py` | Triagem de segurança: regras fixas (camada 1) e decisão final com o modelo (camada 2) |
| `guidelines.py` | Regras fixas do produto: nome da MarIA, perguntas de tom, lista "nunca dizer" |
| `handoff.py` | Assumir, devolver, responder pelo painel, pedido de humano, recusa do bot, "Em consulta" |
| `notifications.py` | E-mail de alerta para a profissional e registro do resultado na trilha |
| `auth.py` | Login com Google, lista de convidados, sessões, `current_user` e limite de tentativas |

## 4. O canal é desacoplado do núcleo

Esta é a decisão de arquitetura mais importante para o projeto conseguir
evoluir. O núcleo (triagem, RAG, resposta) nunca sabe se a mensagem veio
do WhatsApp, do simulador do painel ou, no futuro, do Instagram.

Cada canal precisa apenas:

1. Traduzir o que chega para um par simples: *quem falou* (identificador
   no canal) e *o que falou* (texto).
2. Saber entregar a resposta de volta.

```
  WhatsApp  ─┐
             ├─→  [ identificador + texto ]  →  núcleo  →  resposta
  Simulador ─┘
```

Consequências práticas:

- Dá para desenvolver e demonstrar tudo pelo simulador, sem depender da
  Meta estar no ar.
- Um canal novo é um arquivo novo, não uma alteração espalhada.
- A mesma triagem protege todos os canais, sem duplicação.

O **simulador** não é um atalho nem um protótipo separado: ele passa
exatamente pelo mesmo caminho do WhatsApp, com o `session_id` fazendo o
papel do número de telefone. O que funciona nele funciona no WhatsApp.

## 5. Multi-tenant desde o começo

Nenhuma consulta tem profissional fixo no código. Cada profissional tem:

- suas conversas e contatos, isolados por `professional_id`;
- sua coleção própria no ChromaDB (`prof-{slug}`), então um documento de
  uma nunca aparece na resposta da outra;
- seu tom de voz e sua agenda do Google.

As rotas de gestão exigem sessão (`auth.current_user`), e a conta
logada aponta para um `professional_id`. Toda rota confere se o dado
pedido é dessa profissional; se não for, responde 404, como se não
existisse. O `slug` continua na URL, mas não dá acesso a nada sozinho.

O painel chama a API em `/api`, no mesmo endereço dele: em
desenvolvimento, o proxy do Vite repassa para o backend; em produção,
o servidor web faz o mesmo. Isso mantém o cookie de sessão no mesmo
site.

## 6. O que ainda não existe

Estas peças estão desenhadas mas não construídas. A ordem está no
[plano do MVP](../planejamento-mvp-9out.md).

- **Triagem de mensagens quebradas**: juntar as últimas mensagens do
  contato antes de avaliar.
- **Webhook do WhatsApp**: receber com validação de assinatura,
  deduplicar reenvios e responder pela API da Meta.
- **Agenda**: ler disponibilidade e criar evento provisório.
