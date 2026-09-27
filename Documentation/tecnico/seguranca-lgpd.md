# Segurança e LGPD

O MarIA lida com dados sensíveis: mensagens de pessoas em sofrimento
emocional procurando atendimento psicológico. Este documento reúne as
proteções implementadas, o protocolo de risco e o que ainda falta.

---

## 1. Princípios

Combinados no [planejamento do projeto](../planejamento-projeto.md) e
na entrevista de protocolo com a profissional:

1. O sistema **nunca** diagnostica nem dá aconselhamento clínico.
2. A triagem de segurança roda **antes de tudo** e, em emergência,
   segue um caminho fixo e previsível — sem improviso do modelo.
3. Na dúvida, prefere-se o alarme falso. Mas **só dentro da categoria de
   risco à vida**: linguagem de sofrimento, comum no nicho da
   profissional, não dispara emergência sozinha.
4. O protocolo é uma **decisão clínica**, não técnica. Os critérios e o
   texto de emergência foram definidos pela profissional.
5. Nenhum dado real de paciente entra no sistema antes de ela testar e
   aprovar.

## 2. Criptografia em repouso

Cifrados no banco (Fernet, chave simétrica em `DATA_ENCRYPTION_KEY`):

- conteúdo de todas as mensagens
- identificador do contato (telefone, no WhatsApp)
- nome de perfil do contato
- trecho que disparou um alerta

Quem olha o PostgreSQL direto vê apenas cifras. A aplicação decifra de
forma transparente, pelo tipo `EncryptedText`.

A cifragem é **não-determinística**: o mesmo texto gera cifras
diferentes a cada gravação. Isso impede descobrir, só olhando o banco,
que duas conversas são da mesma pessoa. Como consequência, não dá para
buscar por um valor cifrado — daí o índice cego descrito no
[modelo de dados](modelo-de-dados.md#por-que-existe-o-índice-cego).

**Não** são cifrados: nome e tom de voz da profissional, nomes de
arquivos, e o texto dos documentos indexados no ChromaDB (material
institucional dela, não dado de paciente).

## 3. Transparência: aviso de IA

Toda conversa nova recebe, antes de qualquer resposta, um aviso de que
se trata de um assistente virtual.

O aviso é **determinístico**: um texto fixo, enviado pelo código, e não
uma instrução para o modelo se apresentar. Um modelo pode esquecer ou
reformular; uma obrigação de transparência não pode depender disso.

O texto atual está em `app/routers/chat.py`. Ele ainda **aguarda
aprovação final da profissional**, que na entrevista disse precisar
pensar melhor em como quer comunicar isso.

## 4. Retenção de dados

Conversas sem atividade há mais de `DATA_RETENTION_DAYS` (padrão: 90)
são apagadas, junto com mensagens e alertas. A contagem usa a **última
mensagem**, não a data de criação: uma conversa ativa por meses não é
apagada por ter começado há muito tempo.

Hoje a limpeza é manual
(`python scripts/purge_old_conversations.py`), porque não há dados reais
em produção. Agendar isso é item das semanas seguintes ao MVP.

Duas coisas pedidas pela profissional ainda não existem:

- **Retenção diferente para paciente e lead.** O campo `contact_type` já
  está no modelo; a política ainda é uniforme.
- **Guardar telefone para marketing.** Exige base legal e consentimento
  próprios, separados do consentimento para atendimento. Fora do escopo
  do MVP por essa razão, não por falta de tempo.

## 5. Protocolo de risco

Os critérios abaixo foram definidos pela profissional e são a
especificação que o módulo de triagem deve seguir. O detalhamento está
em [requisitos](../levantamento-requisitos-mvp.md#7-critérios-de-triagem-já-aprovados-pela-marília-resumo-operacional).

### Os níveis, e por que a distinção importa

| Nível | O que dispara | O que o sistema faz |
|---|---|---|
| **Emergência** | Indicação clara de risco à vida: se machucar, plano ou tentativa em andamento, violência ou perigo imediato | Interrompe o fluxo normal, envia o texto fixo aprovado com SAMU 192, 190 e CVV 188, registra alerta e avisa a profissional |
| **Dúvida sobre segurança** | Desejo de morrer com intenção incerta ("quero morrer" isolado), rotulado assim pela Marília em 23/09 | Registra alerta e avisa a profissional; o bot segue |
| **Sofrimento intenso** | Sofrimento relacional forte, sem indicação de risco à vida | Marca a conversa como "necessita atenção" e segue atendendo normalmente |

Há ainda um alerta que **não é de risco**: `bot_refused`, quando a pessoa
recusa falar com um bot. Usa a mesma trilha para chegar à profissional,
mas fica fora das métricas da triagem. Detalhes em
[triagem de segurança](../funcionalidades/triagem-de-seguranca.md) e
[handoff](../funcionalidades/handoff-e-em-consulta.md).

A profissional atende principalmente questões de relacionamento. Frases
como "preciso de ajuda", "estou desesperada", "perdi meu chão" ou "não
consigo continuar assim" são o vocabulário cotidiano de quem a procura.
Tratá-las como emergência geraria alarme constante e tornaria o sistema
inútil. Por isso o segundo nível existe: sem ele, o sistema ou ignoraria
sofrimento real, ou gritaria o tempo todo.

Ela foi explícita sobre o contexto: *"não consigo continuar nesse
relacionamento" é diferente de "não consigo continuar vivendo"*.

### Regras do caminho de emergência

- O texto é **fixo e aprovado**. Não é gerado pelo modelo e não deve ser
  alterado no código sem nova aprovação clínica.
- A mensagem **não promete** que a profissional vai assumir a conversa,
  responder logo ou acompanhar a crise. O canal não é plantão.
- Depois do encaminhamento, o bot **para** de falar sobre valores,
  planos e agendamento.
- A pessoa **pode voltar** depois para agendar normalmente. Um episódio
  de risco não encerra o relacionamento com o consultório.

### Auditabilidade

Alertas não podem ser editados nem apagados pela profissional, apenas
marcados como revisados. A situação é registrada como eventos
acrescentados, preservando quando disparou, quando foi visto e quando
foi revisado. Ver
[modelo de dados](modelo-de-dados.md#por-que-a-situação-do-alerta-não-é-uma-coluna).

O aviso por e-mail também entra na trilha (`notified` ou
`notify_failed`, com o motivo), para que um alerta que não chegou à
profissional não passe despercebido. O e-mail **não leva conteúdo da
conversa**: sai do sistema e ficaria no provedor dela, fora da cifra e
da retenção. Ver [alerta por e-mail](../funcionalidades/alerta-por-email.md).
O e-mail de pedido para falar com a profissional segue a mesma regra.

Na tela de Conversas, o número do contato aparece mascarado na lista
(`+55 21 •••••-4444`) e completo só na conversa aberta, onde ela pode
precisar ligar para a pessoa numa emergência. Ver
[Conversas](../funcionalidades/conversas.md).

Ela pediu esse registro para poder avaliar depois se o sistema
classificou corretamente — é insumo do ajuste do protocolo, e também dos
resultados do TCC.

### Falha fechada

Se a classificação falhar (erro de rede, tempo esgotado, resposta
inesperada do modelo), o sistema **não segue como se nada tivesse
acontecido**: a mensagem é tratada como "dúvida sobre segurança", o
alerta é registrado e a profissional é avisada. Seguir sem avisar
ninguém diante de uma falha é inaceitável num canal onde pode haver
risco à vida.

## 6. Segredos

| Onde | O quê |
|---|---|
| `backend/.env` | Chaves de API, token da Meta, chave de criptografia, senha do e-mail de envio |
| `backend/secrets/` | Chave da conta de serviço do Google |

Ambos estão no `.gitignore`. Em produção, os arquivos são criados
direto no servidor, com leitura restrita ao usuário do serviço.

Se um segredo vazar: gerar um novo e revogar o antigo (na Anthropic, no
console; na Meta, "Anular tokens" no usuário de sistema). A exceção é a
`DATA_ENCRYPTION_KEY`, que não pode ser simplesmente trocada sem
recifrar os dados existentes.

Logs **não devem registrar conteúdo de mensagem**. Se um serviço de
monitoramento de erros for adotado, precisa estar configurado para
descartar corpo de requisição — caso contrário, conversa clínica
vazaria para um terceiro.

## 7. Acesso ao painel

- **Login com Google** ([detalhes](../funcionalidades/login-com-google.md)):
  a MarIA não guarda senha; o backend confere a assinatura do token do
  Google e se o e-mail está verificado.
- **Só convidados** (`ALLOWED_EMAILS`), conferido também a cada
  requisição: tirar alguém da lista corta o acesso na hora.
- **Sessão** em cookie `httpOnly`, `SameSite=Lax` e `Secure` em
  produção; o banco guarda só o hash do código. Expira em 7 dias.
- **Isolamento:** cada rota confere se o dado é da profissional logada
  e responde 404 quando não é.
- **Limite de tentativas de login:** 10 a cada 5 minutos por IP.

Dados pessoais da conta: e-mail, nome, foto (endereço) e o
identificador do Google.

## 8. O que ainda falta

Antes de qualquer paciente real usar o sistema:

- [x] Módulo de triagem implementado e testado com os cenários que a
      profissional listou (resultado v1 em 23/09; falta conjunto de teste novo)
- [ ] Triagem de mensagens quebradas em várias partes
- [ ] Textos fixos de handoff aprovados por ela
- [ ] Ela revisar os resultados, incluindo falsos positivos e negativos
- [ ] Texto do aviso de IA aprovado por ela
- [x] Login protegendo as rotas de gestão (27/09)
- [ ] Assinatura do webhook validada (senão qualquer um injeta mensagem)
- [ ] Limite de requisições por contato
- [ ] Política de privacidade e termos publicados
- [ ] Backup do banco, com restauração testada
- [ ] Retenção automatizada
