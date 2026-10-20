# Conectar o WhatsApp pelo painel

> Situação: funcionando. Testado de verdade em 19/10/2026 com o número da Marília. Última atualização: 19/10/2026.

## O que é

A profissional conecta o número de atendimento sem sair do painel: digita
o número e o nome que vai aparecer no WhatsApp, recebe um código por SMS
(ou ligação) no chip, digita o código e pronto. A partir daí, quem
escreve para esse número é atendido pela SelenIA, e ela responde pelo
painel. Fica na etapa 6 do [cadastro](cadastro-em-etapas.md) e na tela
**WhatsApp** do menu lateral (`/whatsapp`), para quem pulou a etapa.

## Por que existe

Sem isso, ligar um número a uma profissional era trabalho manual do
Pedro (pegar o "phone number ID" na Meta e gravar no banco), como foi
feito com o número de teste em 27/09. Para a SelenIA servir a outras
profissionais, a conexão precisa ser feita por quem usa.

Decisões:
- **Número dedicado à SelenIA** (Pedro, 26/09/2026): o número sai do
  aplicativo do WhatsApp e a profissional responde pelo painel. Manter o
  número no celular junto (coexistência) exige ser Tech Provider da Meta
  (verificação da empresa com CNPJ, revisão do app e domínio com HTTPS):
  trabalho futuro.
- **Sem verificar a empresa antes da defesa** (Pedro, 26/09/2026): a
  conta fica limitada a 2 números, o suficiente para o MVP.
- **Prevista para 05/10, construída em 13/10** (atraso da semana 3). Na
  ordem de corte, é o terceiro item: sem o chip, a demo usa o número já
  conectado.

## Como usar

1. No cadastro (etapa 6) ou em **WhatsApp**, no menu, leia o aviso:
   o número deixa de funcionar no aplicativo do WhatsApp.
2. Digite o número com DDD e confira o nome que vai aparecer.
3. Clique em **Enviar código por SMS** (ou **Receber por ligação**, se o
   chip não recebe SMS).
4. Digite o código de 6 números e clique em **Confirmar código**. A
   SelenIA verifica e registra o número em seguida.
5. Pronto: aparece "WhatsApp conectado", com o número e se o nome já foi
   aprovado pelo WhatsApp.

Se o código não chegar, use **Reenviar por SMS** ou **Receber por
ligação**. **Trocar o número** volta ao início. Se o código foi aceito
mas o registro falhou, a tela mostra **Registrar número** para tentar de
novo, com a conta de tentativas, e **Trocar o número**. Se a Meta
responder que o número não está verificado, a tela volta sozinha para a
etapa do código.

### Depois de conectado

- **Trocar o nome**: digite o nome novo e clique em **Enviar para
  análise**. O WhatsApp analisa (em geral de 1 a 2 dias) e, até lá,
  continua o nome atual. Quando aprovar, aparece **Aplicar nome novo**:
  esse clique registra o número de novo, que é o que a Meta exige para o
  nome novo aparecer. Se o WhatsApp recusar, a tela avisa, o nome atual
  continua e o botão **Pedir outro nome** abre o pedido de novo.
- Quando o WhatsApp responde (aprovado ou recusado), aparece uma
  bolinha vermelha no item **WhatsApp** do menu. Ela some depois de
  aplicar o nome aprovado, ou ao abrir a tela, no caso de recusa. Não
  precisa esperar a análise para usar o app: até lá tudo funciona com o
  nome antigo.
- **Trocar o número**: depois de confirmar, a SelenIA para de responder
  por aquele número na hora e a tela volta para conectar outro. As
  conversas antigas continuam no painel.

## Como funciona

Quatro chamadas à Graph API da Meta, todas pelo backend, na conta do
WhatsApp Business do produto (`WHATSAPP_BUSINESS_ACCOUNT_ID`):

1. `POST /{waba}/phone_numbers` com `cc`, `phone_number` e
   `verified_name` cadastra o número. Antes, o backend procura o número
   na conta (`GET /{waba}/phone_numbers`): se já estiver lá, de outra
   tentativa, reaproveita, porque a conta só comporta 2 números.
2. `POST /{id}/request_code` (`SMS` ou `VOICE`, idioma `pt_BR`). Se a
   Meta responder que o número já está verificado (erro 136024), pula
   para o registro.
3. `POST /{id}/verify_code` com o código.
4. `POST /{id}/register` com `messaging_product` e um PIN de 6 dígitos
   da verificação em duas etapas, gerado na primeira vez e guardado
   cifrado (é o mesmo PIN se o número for registrado de novo).

Até o registro, o número fica **pendente** (`whatsapp_pending_id`) e não
recebe mensagens. Depois do registro vira `whatsapp_phone_number_id`, e
o webhook já leva as mensagens dele à profissional: o app está inscrito
na conta inteira, então número novo não precisa de configuração.

Regras:
- Só números do Brasil (+55), com DDD.
- Uma profissional, um número. Um número já ligado a outra conta da
  SelenIA é recusado.
- Registro: a Meta aceita 10 por número em 72 horas, e o 11º bloqueia o
  número por mais 72 horas. O painel para em 8 (margem para registros
  feitos fora dele) e conta cada tentativa em
  `whatsapp_register_attempts`.
- Erros da Meta aparecem na tela com a mensagem dela e o código, para dar
  para pesquisar; os conhecidos (133016 bloqueio, 133005 PIN diferente)
  têm explicação própria.

Arquivos: `services/whatsapp_numbers.py` (os passos e as regras),
`services/whatsapp.py` (`_graph`, `MetaError`), rotas
`/professionals/{slug}/whatsapp` em `routers/professionals.py`,
`components/WhatsAppConnect.jsx` (usado em `onboarding/Steps.jsx` e
`pages/WhatsApp.jsx`).

## Textos fixos

Nenhum texto enviado às pessoas. As mensagens da tela são do painel.

## Configuração

- `WHATSAPP_BUSINESS_ACCOUNT_ID`: a conta (WABA). Sem ela, a tela diz que
  a conexão não está configurada e o cadastro segue por "Conectar depois".
- `WHATSAPP_ACCESS_TOKEN` precisa da permissão
  `whatsapp_business_management` (conferido em 13/10 com uma leitura dos
  números da conta).
- Campos da profissional: `whatsapp_phone_number_id`,
  `whatsapp_pending_id`, `whatsapp_setup_step`,
  `whatsapp_display_number`, `whatsapp_verified_name`, `whatsapp_pin`
  (ver [modelo de dados](../tecnico/modelo-de-dados.md)).

## Segurança e LGPD

O número é da profissional, não de paciente, e fica em texto (aparece na
tela dela). O PIN da verificação em duas etapas fica cifrado, nunca sai
na resposta da API nem nos logs; o código do SMS só passa pela Meta e
não é gravado. Todas as rotas exigem login e só a própria profissional
mexe no número dela.

## Limitações e pendências

- **Teste real feito em 19/10/2026** com o número da Marília: conectou depois de dois tropeços que viraram
  correção (limite de 2 números da conta e "número não verificado" no
  registro). Trocar o nome e trocar o número ainda não foram usados de
  verdade, só com a Meta simulada.
- **Trocar o número** desliga o número da Cloud API (`deregister`), mas
  não apaga da conta da Meta: apagar é só pelo WhatsApp Manager. Como a
  conta sem verificação de empresa comporta 2 números, para cadastrar
  outro pode ser preciso apagar o antigo lá antes.
- Hoje a conta tem os 2 números ocupados: +55 21 95952-4339 (Pedro,
  ainda com o nome "MarIA Assistente Virtual") e o da Marília
  (conectado em 19/10/2026).
- A Meta limita `deregister` a 10 vezes por número em 72 horas. A tela
  não conta essas vezes (troca de número é rara).
- Aplicar o nome novo conta no limite de registros, como o primeiro.
- O nome passa pela análise do WhatsApp; até ser aprovado, as pessoas
  veem só o número.

## Como testar

Automático: `tests/test_whatsapp_numbers.py` (formatos de número, fluxo
completo até o registro, código errado, reenvio por ligação, número já
na conta, número já verificado, limite de registros, bloqueio da Meta
explicado e contado, número de outra conta, profissional já conectada,
cancelar, servidor sem WABA, número ligado à mão).

Manual, com o chip (precisa de um número que nunca esteve no WhatsApp):
1. Use uma conta sem número conectado: a conta `pedro-costa` já tem o
   número de teste. O mais simples é convidar um segundo e-mail em
   `ALLOWED_EMAILS` e fazer o cadastro com ele.
2. Na etapa 6, digite o número do chip e envie o código por SMS.
3. Digite o código. Deve aparecer "WhatsApp conectado".
4. De outro celular, mande "oi" para o número novo: a SelenIA responde e
   a conversa aparece em Conversas, na conta nova.
5. Anote qualquer erro da Meta (mensagem e código) para ajustar a tela.

## Histórico

- 13/10/2026: primeira versão (cadastro, código por SMS ou ligação,
  verificação, registro com PIN cifrado, limite de registros, etapa 6 e
  tela WhatsApp do menu, que sai do "Em breve").
- 19/10/2026: **Trocar o número** também na etapa de registrar; se o
  registro falha e a Meta diz que o número não está verificado
  (`code_verification_status`), volta para a etapa do código em vez de
  prender a tela em "Registrar número" (caso real no cadastro da Marília).
- 19/10/2026: depois de conectado, **Trocar o nome** (`new_display_name`,
  análise da Meta, **Aplicar nome novo** registra de novo) e **Trocar o
  número** (`deregister`). Rotas `POST /professionals/{slug}/whatsapp/name`,
  `POST .../whatsapp/name/apply` e `DELETE /professionals/{slug}/whatsapp`
  (pedido do Pedro).
- 19/10/2026: bolinha vermelha no item WhatsApp do menu quando a Meta
  responde sobre o nome novo (`PanelLayout.jsx` consulta a cada 5
  minutos; `nameNeedsAction` em `WhatsAppConnect.jsx`). Nada é feito
  sozinho: aplicar continua sendo um clique (pedido do Pedro).
- 19/10/2026: a Revisão do cadastro (etapa 7) mostra o número conectado
  (`GET /professionals/{slug}/whatsapp`); antes dizia sempre "Não
  conectado".
- 19/10/2026: teste real feito (número da Marília conectado).
