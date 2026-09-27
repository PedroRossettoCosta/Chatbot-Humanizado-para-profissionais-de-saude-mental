# Alerta por e-mail

> Situação: funcionando; falta configurar a conta que envia. Última atualização: 25/09/2026.

## O que é

Quando a triagem gera um alerta, ou quando alguém recusa falar com a
MarIA, a profissional recebe um e-mail na hora, sem precisar estar com
o painel aberto.

## Por que existe

A Marília pediu para ser avisada na hora, de preferência por WhatsApp
(protocolo de 16/09/2026). O aviso por WhatsApp exige um template
aprovado pela Meta; o e-mail é o caminho que não depende disso e fica
como reserva quando o WhatsApp existir.

Decisões:
- **Cada profissional configura o endereço** onde recebe (Pedro,
  25/09/2026). Quem envia é uma conta só, do produto: nenhuma
  profissional cadastra senha de e-mail no sistema.
- **Nenhum conteúdo da conversa no e-mail** (proposta de 25/09/2026, a
  validar com o Thiago ou a Marília). O e-mail sai do sistema e fica no
  provedor dela, fora da cifra e da retenção de 90 dias.

## Como usar

1. No cadastro (etapa 1) ou depois em **Perfil do atendimento**,
   preencha **E-mail para alertas** e clique em **Salvar alterações**.
2. Quem administra o sistema configura a conta de envio no
   `backend/.env` (ver Configuração).

## Como funciona

| Tipo de alerta | Assunto do e-mail |
|---|---|
| Emergência | "[MarIA] EMERGÊNCIA: possível risco à vida" |
| Dúvida sobre segurança | "[MarIA] Alerta: dúvida sobre segurança" |
| Recusa do bot | "[MarIA] Uma pessoa quer falar com você" |

Sofrimento intenso **não** gera e-mail, só a marcação "necessita atenção".

O corpo traz: o que aconteceu e o que a MarIA fez, horário de Brasília,
canal e o link do painel.

O envio roda **depois** da resposta ao contato (tarefa em segundo
plano), para que um servidor de e-mail lento não atrase a mensagem de
emergência.

O resultado vai para a trilha do alerta:
- `notified`, com o endereço de destino na nota;
- `notify_failed`, com o motivo: sem e-mail configurado, envio não
  configurado (SMTP) ou erro no envio.

Arquivos: `services/notifications.py`, `routers/chat.py`,
`services/handoff.py`.

## Textos fixos

Os três assuntos e explicações em `notifications._LEVEL_TEXT`. Não
precisam da aprovação clínica (vão para a profissional, não para o
contato), mas vale ela ler.

## Configuração

No `backend/.env`:

| Variável | Exemplo |
|---|---|
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | `conta-que-envia@gmail.com` |
| `SMTP_PASSWORD` | senha de app do Gmail (16 letras) |
| `SMTP_FROM` | `MarIA <conta-que-envia@gmail.com>` |

Para o Gmail: Conta Google → Segurança → Verificação em duas etapas →
Senhas de app. Não use a senha normal da conta.

Campo da profissional: `alert_email`.

## Segurança e LGPD

- Nada da conversa no e-mail nem no log de erro.
- A senha de envio fica só no `.env`, fora do Git.
- A nota do evento `notified` guarda o endereço de destino, que é da
  profissional, não do contato.

## Limitações e pendências

- **Falta a conta de envio** no `.env`. Até lá, todo alerta registra
  `notify_failed`.
- Sem tela de alertas (02/10) e sem deploy, o link do e-mail só abre o
  painel no computador onde o sistema roda.
- Não há nova tentativa automática quando o envio falha; a falha fica
  registrada.
- Aviso por WhatsApp (template da Meta) ainda não existe.

## Como testar

Automático: `tests/test_notifications.py`. Nenhum teste envia e-mail de
verdade: `tests/conftest.py` substitui o envio.

Manual: com o `.env` configurado e o e-mail preenchido no painel,
mande "to pensando em me matar" no simulador e confira a caixa de
entrada (e o spam).

## Histórico

- 25/09/2026: e-mail de alerta, campo por profissional, trilha de envio.
