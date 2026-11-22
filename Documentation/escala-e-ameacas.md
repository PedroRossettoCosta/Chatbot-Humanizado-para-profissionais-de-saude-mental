# Escala e ameaças à validade: o que muda para atender mil profissionais

Anotado em 15/11/2026, a pedido do Pedro. **Não é escopo da defesa
atual.** Serve para duas partes do texto do TCC:

- **Ameaças à validade / limitações:** o que o MVP não prova, porque
  roda numa escala pequena e com decisões que só valem para poucas
  profissionais.
- **Trabalhos futuros:** o que precisaria mudar para oferecer a SelenIA
  a mil profissionais.

O MVP valida o produto (triagem, atendimento, alertas, agenda) com uma
profissional real e uma de teste. Esta lista é a distância entre
"validado" e "em escala".

## 1. WhatsApp: cada profissional com a própria conta na Meta

**Hoje:** todos os números ficam no portfólio da Meta do Pedro (uma WABA
só), e o token de acesso é um só, no `.env`.

**Por que não escala:**
- Limite de números registrados por portfólio: **2 sem verificação da
  empresa; 20 com a empresa verificada** (ou ao chegar no limite de
  2.000 mensagens). A página da Meta não diz como passar de 20.
- **A profissional não controla o próprio número:** apagar um número da
  conta só é possível no WhatsApp Manager, por quem administra o
  portfólio ("You can't delete a business phone number via the API").
  O botão **Remover número** do painel desregistra o número da Cloud
  API, mas não o apaga da conta. Se o aplicativo do WhatsApp só aceitar
  o número de volta depois de apagado (a confirmar no teste com a
  Marília), ela depende de quem administra a conta.
- Qualidade e bloqueios ficam concentrados: um consultório com problema
  afeta a conta de todos.
- O número fica exclusivo da SelenIA (sai do aplicativo do WhatsApp), a
  maior barreira para quem já atende pelo WhatsApp.

**Caminho:** virar **Tech Provider** da Meta e usar o **Embedded
Signup**. No cadastro, a profissional abre a janela da Meta, cria ou
escolhe a própria conta (portfólio e WABA) e autoriza o app da SelenIA.
- O número é dela, com o próprio WhatsApp Manager.
- O limite de números é por profissional.
- Qualidade, bloqueios e cobrança da Meta ficam separados.
- O mesmo fluxo permite a **coexistência** (o número continua no
  aplicativo do WhatsApp Business e também na SelenIA). Conferir se está
  disponível no Brasil para este caso.

**Pré-requisitos:** CNPJ e verificação da empresa na Meta; revisão do
app com acesso avançado a `whatsapp_business_management` e
`whatsapp_business_messaging`; cadastro como Tech Provider. A análise da
Meta leva semanas, por isso é o primeiro passo.

**No código:** trocar o fluxo de "Conectar WhatsApp"
(`services/whatsapp_numbers.py`) pelo Embedded Signup; guardar token e
WABA **por profissional** (cifrados), em vez do token global; inscrever
o app nos webhooks de cada WABA. O caminho da mensagem quase não muda:
o webhook já roteia por `phone_number_id`.

**Custo da Meta:** desde 01/10/2026 a Meta cobra por mensagem também
as mensagens de serviço (as respostas dentro da janela de 24h, que eram
grátis desde 01/11/2024). Cada número tem **1.000 mensagens de serviço
grátis por mês**; a cobrança começa na 1.001ª, e só com forma de
pagamento cadastrada (sem ela, o que passa de 1.000 não é enviado).
Contam as respostas da SelenIA, as da profissional pelo painel e os
textos fixos (aviso de IA, emergência, confirmações, link do Meet). Com
um número por profissional, um consultório cheio (cerca de 280 respostas
por mês, mais os textos fixos) fica dentro da franquia. Em escala, cada
profissional precisa de forma de pagamento na própria conta para não
travar no limite. Conferir a tabela vigente antes de qualquer plano de
preço.

## 2. Infraestrutura

**Hoje:** um serviço só na Railway (plano de teste), uma réplica,
ChromaDB num volume local, Postgres sem backup automático.

- **Várias réplicas:** as rotinas de fundo (vencimento de pedidos,
  resumo do fim da consulta) rodariam em dobro. Precisam de um worker
  separado ou de uma trava no banco.
- **ChromaDB no volume** prende o sistema a uma máquina. Trocar por
  **pgvector** no próprio Postgres: um banco a menos, com backup junto.
- **Fila no webhook:** responder 200 à Meta na hora e processar a
  mensagem num worker; hoje o processamento roda na requisição.
- **Postgres gerenciado** com backup e réplica.
- **Monitoramento e alerta de erro** (Sentry ou similar): o fluxo de
  emergência é crítico, e uma falha precisa avisar alguém na hora.
- **Plano pago da hospedagem:** também libera SMTP e IP fixo de saída
  (hoje o e-mail vai pela API da Brevo por causa do bloqueio de SMTP).
- `railway.json` está descontinuado e só funciona até 01/12/2026
  (migrar para `.railway/railway.ts`).

## 3. Contas, acesso e e-mail

- **Google:** `calendar.events` é escopo sensível. Sem a verificação do
  app pelo Google, só até 100 usuários de teste conseguem conectar a
  agenda.
- **Cadastro aberto:** hoje o acesso é por lista (`ALLOWED_EMAILS`).
  Em escala, cadastro aberto com assinatura e pagamento.
- **E-mail:** domínio próprio com DKIM e DMARC na Brevo (hoje o
  remetente é um Gmail, e os alertas podem cair no spam) e plano que
  aguente o volume (o grátis tem 300 e-mails por dia).

## 4. Custo do modelo

- Custo por profissional ativa (triagem e resposta), que precisa caber
  no preço da assinatura. Valores confirmados em 21/11/2026 pela tabela
  `llm_usage` (13/10 a 05/11, 9 conversas de teste, banco local):
  **US$ 0,0108 por mensagem na triagem** e **US$ 0,0098 por resposta**.
  Os dois são médias; na resposta, as chamadas da mesma resposta
  (consulta à agenda) contam juntas. Substituem os US$ 0,0103 e
  US$ 0,0119 da versão anterior. Detalhes e conta em
  [2026-11-21-custo-isolamento-t4.md](resultados-testes/2026-11-21-custo-isolamento-t4.md).
  Aplicados à estimativa do consultório cheio (seção 1: 350 mensagens e
  280 respostas por mês), dão uma ordem de grandeza, não um custo
  medido:

  | | 1 profissional | 50 profissionais (por profissional) |
  |---|---|---|
  | Triagem: 350 × 0,0108 | US$ 3,78 | US$ 3,78 |
  | Respostas: 280 × 0,0098 | US$ 2,74 | US$ 2,74 |
  | Railway | US$ 5,00 (Hobby) | US$ 0,40 (Pro ÷ 50) |
  | Vercel | US$ 0 (Hobby) | US$ 0,40 (Pro ÷ 50) |
  | **Total por mês** | **US$ 11,52** | **US$ 7,32** (US$ 366,00 para as 50) |

  Com os valores antigos (0,0103 e 0,0119), o artigo dizia US$ 11,93 e
  US$ 7,73. WhatsApp (dentro da franquia) e e-mail (plano grátis da
  Brevo) entram a US$ 0.
- Limites de requisição da Anthropic por nível de conta.
- Cache de prompt: o perfil da profissional se repete em toda mensagem.
- Teto de uso **por profissional**, além do que já existe por contato,
  para uma conta não estourar o custo.

## 5. LGPD e responsabilidade clínica

- Conversa de saúde mental é **dado sensível**. Em escala:
  - contrato de operador com cada profissional (ela controla, a
    SelenIA opera);
  - encarregado de dados (DPO);
  - política de retenção revisada;
  - gestão das chaves de criptografia;
  - contratos com os suboperadores (Meta, Anthropic, Google,
    hospedagem, Brevo).
- Textos fixos de emergência e regras de triagem passam a valer para
  milhares de pacientes: revisão clínica formal, além da Marília.

## 6. Ameaças à validade do MVP (para o texto)

- **Escala:** testado com uma profissional real e uma de teste; nada
  disso mostra o comportamento com muitos consultórios ao mesmo tempo.
- **Viés de avaliação:** a principal usuária de teste é irmã do autor.
- **Uma conta da Meta para todos:** decisão que só vale para poucas
  profissionais (seção 1).
- **Infraestrutura de teste:** plano de teste da Railway, uma réplica,
  sem backup automático nem monitoramento.
- **Dependências externas:** Meta, Anthropic, Google, Railway e Brevo;
  uma mudança de regra ou de preço de qualquer uma afeta o produto.
- **Remetente Gmail:** os alertas por e-mail podem cair no spam.

## Ordem sugerida

1. CNPJ, verificação da empresa na Meta, Tech Provider e Embedded
   Signup (o que mais demora e o que destrava o resto).
2. Verificação do app no Google e domínio próprio de e-mail.
3. pgvector, worker para rotinas e webhook, monitoramento.
4. Cadastro aberto com assinatura e limite de custo por conta.
5. Estrutura de LGPD e revisão clínica.

## Fontes

- Meta, números de telefone (limite de números e exclusão só pelo
  WhatsApp Manager):
  https://developers.facebook.com/documentation/business-messaging/whatsapp/business-phone-numbers/phone-numbers
- Meta, registro e `deregister`:
  https://developers.facebook.com/docs/whatsapp/cloud-api/reference/registration
