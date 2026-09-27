# Funcionalidades

Um documento por funcionalidade: o que é, por que existe, como usar e
como funciona. Os documentos técnicos (`../tecnico/`) explicam as peças
do sistema; estes explicam o que a profissional vê e o que a MarIA faz.

Toda mudança de funcionalidade atualiza o documento dela no mesmo
commit (regra em [`CLAUDE.md`](../../CLAUDE.md)).

| Funcionalidade | Situação | Resumo |
|---|---|---|
| [Triagem de segurança](triagem-de-seguranca.md) | Funcionando | Detecta risco em cada mensagem antes do modelo responder, em duas camadas |
| [Perfil e regras da MarIA](perfil-e-regras-da-maria.md) | Funcionando | Tom de voz, exemplos, valores e a lista fixa do que a MarIA nunca diz |
| [Handoff e "Em consulta"](handoff-e-em-consulta.md) | Funcionando | A profissional assume a conversa; pedido de humano; recusa do bot |
| [Login com Google](login-com-google.md) | Funcionando, falta o Client ID | Entrada no painel pela conta Google, só para convidados; rotas protegidas |
| [Alerta por e-mail](alerta-por-email.md) | Funcionando, falta a conta de envio | Avisa a profissional fora do painel quando há alerta |

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
