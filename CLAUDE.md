# Instruções do projeto MarIA

MarIA é a assistente virtual de atendimento inicial para profissionais
de saúde mental, desenvolvida como TCC. Visão geral no
[README](README.md); plano em andamento em
[planejamento-mvp-9out.md](Documentation/planejamento-mvp-9out.md).

## Documentação faz parte de toda mudança

Uma mudança só está pronta quando a documentação acompanha o código, no
mesmo commit. Isso vale para funcionalidade nova, mudança de
comportamento, texto fixo novo, campo novo e decisão de produto.

### 1. Documento da funcionalidade

Cada funcionalidade tem um arquivo em
[`Documentation/funcionalidades/`](Documentation/funcionalidades/README.md),
seguindo o modelo que está no índice da pasta. Crie o arquivo se a
funcionalidade for nova; atualize se ela mudou. O documento precisa ter:

- **O que é**, em linguagem que a profissional entende.
- **Por que existe**: a decisão, quem tomou e quando (data absoluta).
  Isso alimenta o texto do TCC.
- **Como usar**: o passo a passo no painel, do ponto de vista de quem usa.
- **Como funciona**: o fluxo, as regras e os arquivos do código envolvidos.
- **Textos fixos**: cada mensagem que o sistema envia sem passar pelo
  modelo, e se a Marília já aprovou.
- **Configuração**: variáveis de ambiente e campos da profissional.
- **Segurança e LGPD**: que dado pessoal circula, para onde, e o que foi
  feito para proteger.
- **Limitações e pendências**: o que não faz ainda, o que depende de outra
  entrega, o que precisa de aprovação.
- **Como testar**: os testes automáticos e um roteiro manual no simulador.
- **Histórico**: uma linha por mudança, com data.

### 2. Documentos técnicos afetados

Atualize no mesmo commit o que a mudança tocar:

| Se mudou... | Atualize |
|---|---|
| Tabela ou campo | [modelo-de-dados.md](Documentation/tecnico/modelo-de-dados.md) (e a migração do Alembic) |
| Variável de ambiente | [configuracao.md](Documentation/tecnico/configuracao.md) e `backend/.env.example` |
| Caminho da mensagem, serviço ou rota | [arquitetura.md](Documentation/tecnico/arquitetura.md) |
| Dado pessoal, alerta, triagem ou segredo | [seguranca-lgpd.md](Documentation/tecnico/seguranca-lgpd.md) |
| Arquivo de teste | tabela "O que está coberto" em [desenvolvimento.md](Documentation/tecnico/desenvolvimento.md) |
| O que já funciona | seção "Estado atual" do [README](README.md) |
| Decisão de produto ou mudança de prazo | [planejamento-mvp-9out.md](Documentation/planejamento-mvp-9out.md) (seção 9) |

### 3. Ao terminar

No resumo para o Pedro, diga quais documentos foram criados ou
atualizados. Se algum ficou para depois, diga qual e por quê.

## Convenções

- Documentação e comentários em português, no tom dos documentos
  existentes: direto, explicando o porquê, sem jargão desnecessário.
- **MarIA** é o nome do produto e da assistente em todas as contas, não
  uma configuração da profissional.
- Textos que o sistema envia sem passar pelo modelo (emergência, aviso
  de IA, handoff) são fixos no código, em forma neutra de gênero, e
  precisam da aprovação da Marília antes de uso real.
- Nada de conteúdo de conversa em logs, e-mails ou mensagens de erro.
- **Pronto para a nuvem:** o MVP roda local, mas toda configuração vem
  do `.env`, nada depende de caminho ou endereço fixo da máquina do
  Pedro, e o banco só muda por migração. Regras completas em
  "Pronto para a nuvem" no plano do MVP.
- Commit e push só quando o Pedro pedir.
