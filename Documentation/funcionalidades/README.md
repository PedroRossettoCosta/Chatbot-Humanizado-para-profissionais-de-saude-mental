# Funcionalidades

Um documento por funcionalidade: o que é, por que existe, como usar e
como funciona. Os documentos técnicos (`../tecnico/`) explicam as peças
do sistema; estes explicam o que a profissional vê e o que a SelenIA faz.

Toda mudança de funcionalidade atualiza o documento dela no mesmo
commit (regra em [`CLAUDE.md`](../../CLAUDE.md)).

| Funcionalidade | Situação | Resumo |
|---|---|---|
| [Painel](painel.md) | Funcionando, parte das telas em construção | Menu, "Em consulta" no topo, Perfil do atendimento e o simulador "Testar a SelenIA" |
| [Alertas](alertas.md) | Funcionando | Cada alerta com o trecho, a regra e a trilha de auditoria; marcar como revisado |
| [Atendimento pelo WhatsApp](atendimento-pelo-whatsapp.md) | Funcionando até a Meta; falta publicar o app | Webhook, triagem na hora, espera antes de responder, envio pela API da Meta |
| [Conversas](conversas.md) | Funcionando | Caixa de entrada: quem precisa de você primeiro, assumir, responder, janela de 24h |
| [Base de conhecimento](base-de-conhecimento.md) | Funcionando | Documentos que a SelenIA usa para responder (RAG): enviar e remover |
| [Triagem de segurança](triagem-de-seguranca.md) | Funcionando | Detecta risco em cada mensagem antes do modelo responder, em duas camadas |
| [Perfil e regras da SelenIA](perfil-e-regras-da-maria.md) | Funcionando | Tom de voz, exemplos, valores e a lista fixa do que a SelenIA nunca diz |
| [Handoff e "Em consulta"](handoff-e-em-consulta.md) | Funcionando | A profissional assume a conversa; pedido de humano ("Aguardando você"); recusa do bot |
| [Login com Google](login-com-google.md) | Funcionando | Entrada no painel pela conta Google, só para convidados; rotas protegidas |
| [Cadastro em etapas](cadastro-em-etapas.md) | Funcionando | 7 etapas depois do primeiro login; o painel só abre com o cadastro concluído |
| [Agenda](agenda.md) | Funcionando; textos fixos sem aprovação | Conectar o Google Agenda, horário de atendimento, horários livres, reserva provisória pela SelenIA e confirmar/recusar no painel |
| [Alerta por e-mail](alerta-por-email.md) | Funcionando | Avisa a profissional fora do painel quando há alerta ou pedido para falar com ela |
| [Custo do modelo](custo-do-modelo.md) | Funcionando, sem tela | Tokens de cada chamada sem conteúdo, custo por mês e por conversa (`scripts/custo.py`), cache do prompt |
| [Conectar o WhatsApp](conectar-whatsapp.md) | Funcionando | O número de atendimento conectado pelo painel: SMS, código e registro na Meta; depois, trocar o nome ou o número |
| [Clientes e horário especial](clientes-e-horario-especial.md) | Funcionando | Clientes ativos (automático ao confirmar sessão), tirar e pôr na lista, cliente especial com os próprios dias para marcar a qualquer hora e sem limite por dia |
| [Pedidos para a profissional](pedidos-para-a-profissional.md) | Funcionando | A SelenIA avisa por e-mail e no painel quando a pessoa pede algo que só a profissional decide, sem parar o bot |
| [Limites por contato](limites-por-contato.md) | Funcionando; texto fixo sem aprovação | Até 4 pedidos de horário pendentes e 50 mensagens por hora, por pessoa |

---

## Modelo para um documento novo

Copie a estrutura abaixo. Seções que não se aplicam podem dizer "não se
aplica", mas não devem sumir: a ausência também é informação.

```markdown
# Nome da funcionalidade

> Situação: funcionando | em construção | planejada. Última atualização: DD/MM/AAAA.

## O que é
Duas ou três frases, em linguagem que a profissional entende.

## Por que existe
A necessidade, a decisão e quem decidiu, com data. Alternativas
descartadas e o motivo, quando houver.

## Como usar
Passo a passo no painel (ou do ponto de vista do contato, se for algo
que só ele vê).

## Como funciona
O fluxo e as regras. Arquivos do código envolvidos.

## Textos fixos
Cada mensagem enviada sem passar pelo modelo, e se a Marília aprovou.

## Configuração
Variáveis de ambiente e campos da profissional.

## Segurança e LGPD
Que dado pessoal circula, para onde, e como está protegido.

## Limitações e pendências
O que ainda não faz, o que depende de outra entrega, o que precisa de
aprovação.

## Como testar
Testes automáticos (arquivo) e roteiro manual no simulador.

## Histórico
- DD/MM/AAAA: o que mudou.
```
