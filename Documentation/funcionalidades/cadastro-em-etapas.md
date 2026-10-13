# Cadastro em etapas

> Situação: funcionando; a conexão do WhatsApp (etapa 6) entra em 05/10. Última atualização: 27/09/2026.

## O que é

No primeiro acesso, depois do login com Google, a profissional passa por
7 etapas antes de usar o painel: dados, atendimento, tom de voz, regras
da SelenIA, regras extras, WhatsApp e revisão. Cada "Continuar" grava a
etapa; se ela fechar o navegador, volta de onde parou.

## Por que existe

A SelenIA fala em nome da profissional. Sem valores, apresentação e
exemplos de tom, ela responderia no escuro; sem ler as regras fixas, a
profissional não saberia o que o sistema faz numa emergência.

Decisões:
- **Cadastro obrigatório antes do painel** (Pedro, 26/09/2026): o login
  com Google leva ao cadastro, e só depois ao painel.
- **Seguir o protótipo do Stitch** (Pedro, 27/09/2026), telas C1 a C10
  em `Documentation/TCC App Design/`, sem os textos que o protótipo
  inventou (criptografia de ponta a ponta, conformidade CFM/CFP).
- **Aceite das regras registrado com data e hora**, para ficar claro
  que ela leu o protocolo de risco antes de a SelenIA atender.
- **Duração da sessão como campo próprio**, e não só dentro do texto
  livre do serviço: a agenda precisa do número para montar os horários.
- **Etapa do WhatsApp sem conexão por enquanto**: registrar o número na
  Meta (SMS, código e registro) está no plano para 05/10 e depende do
  segundo chip. Até lá, a etapa mostra o que vai ser pedido e segue por
  "Conectar depois".

## Como usar

1. **Seus dados:** nome de exibição, como a SelenIA deve falar de você
   (feminino, masculino ou neutro, só pelo nome) e e-mail para alertas
   (nome e e-mail já vêm da conta Google).
2. **Atendimento:** especialidade e público, informações do serviço
   (modalidade, frequência, valor, pagamento) e duração da sessão.
3. **Tom de voz:** o tom e, para cada uma das 3 perguntas, uma resposta
   boa e uma ruim. "Ver um exemplo" mostra uma de cada.
4. **Regras da SelenIA:** leia as 11 regras de "nunca dizer" e os 5
   comportamentos em situação de risco, marque "Li e entendi" e
   continue.
5. **Regras extras** (opcional): limites próprios do seu atendimento.
6. **WhatsApp:** por enquanto, clique em "Conectar depois".
7. **Revisão:** confira, use "Editar" para voltar a qualquer etapa e
   clique em **Concluir cadastro**.

Na tela final, "Testar a SelenIA" abre o [painel](painel.md) já no
simulador; "Ir para o painel" abre o painel.

## Como funciona

- Etapa 1 cria a profissional (`POST /professionals`), gera o slug a
  partir do nome e liga à conta. As outras gravam com
  `PATCH /professionals/{slug}`, incluindo `onboarding_step`, a etapa
  alcançada, que nunca volta para trás quando ela edita pela revisão.
- Etapa 4 chama `POST /professionals/{slug}/accept-rules`, que grava
  `rules_accepted_at`.
- "Concluir cadastro" chama `POST /professionals/{slug}/complete-onboarding`,
  que confere tudo o que é obrigatório (`services/onboarding.py`). Se
  faltar algo, responde 422 com a lista, e a revisão mostra "Falta
  preencher". Se estiver completo, grava `onboarding_completed_at`.
- O painel só abre com `onboarding_completed_at` preenchido.
- **Rascunho na página:** o que foi digitado e ainda não passou pelo
  "Continuar" fica guardado no componente do cadastro (`drafts` em
  `Onboarding.jsx`), e não em cada etapa. Assim nada some quando ela vai
  e volta entre as etapas (ex.: sai das regras extras para rever as
  regras fixas). O banco só recebe no "Continuar" (decisão do Pedro,
  27/09/2026); recarregar a página descarta o rascunho.
- Se a etapa 1 tentar criar um cadastro que já existe (outra aba, ou a
  página com dados velhos), o backend responde 409 e a tela busca o
  cadastro existente e segue gravando nele, em vez de travar.
- As regras e os comportamentos de risco vêm de `GET /assistant/guidelines`
  (`services/guidelines.py`), a mesma fonte que o prompt usa. Os
  exemplos de "Ver um exemplo" também vêm de lá e nunca vão para o
  prompt.

Obrigatórios para concluir: nome, pronomes, e-mail para alertas, especialidade e
público, informações do serviço, duração da sessão (15 a 240 minutos),
tom de voz, resposta boa e ruim para as 3 perguntas e o aceite das
regras.

Arquivos: `services/onboarding.py`, `services/guidelines.py`
(`RISK_BEHAVIORS` e exemplos em `VOICE_QUESTIONS`),
`routers/professionals.py`, `frontend/src/pages/Onboarding.jsx`,
`frontend/src/pages/onboarding/Steps.jsx`, `frontend/src/components/ui.jsx`.

## Textos fixos

Nenhum texto vai para o contato. Na tela, `RISK_BEHAVIORS` descreve o
que a triagem e o handoff fazem; se esse comportamento mudar, o texto
muda junto. Os exemplos de resposta boa e ruim são ilustrativos. A
Marília ainda não revisou esses textos.

## Configuração

Campos da profissional: `pronouns`, `session_minutes`, `onboarding_step`,
`rules_accepted_at`, `onboarding_completed_at` (ver
[modelo de dados](../tecnico/modelo-de-dados.md)). Nenhuma variável de
ambiente nova.

## Segurança e LGPD

Os dados são os do perfil da profissional, mais os pronomes. O
gênero não é perguntado à parte: para a SelenIA falar da profissional,
basta o pronome, e a LGPD pede coletar só o necessário. O número de WhatsApp digitado na etapa 6 **não é
salvo** enquanto a conexão não existir. Todas as rotas exigem login e
só a própria profissional mexe no cadastro dela.

## Limitações e pendências

- Etapa 6 (WhatsApp): o envio do SMS e o registro do número entram em
  05/10. As telas "Digite o código" e "WhatsApp conectado" (C7 e C8)
  vêm junto.
- Uma profissional cadastrada antes de 27/09 cai de novo no cadastro, a
  partir da etapa 2, até concluir.
- Textos da etapa 4 e exemplos da etapa 3 sem revisão da Marília.

## Como testar

Automático: `tests/test_onboarding.py` (etapa salva, limites da
duração, o que falta para concluir, aceite e conclusão, regras expostas
pela API).

Manual:
1. Rode `iniciar.bat` e entre com o e-mail convidado.
2. Passe pelas etapas. Na 3, abra "Ver um exemplo"; na 4, confira que
   "Continuar" só libera com a caixa marcada.
3. No meio do cadastro, feche o navegador e entre de novo: volta na
   etapa em que parou.
4. Na revisão, use "Editar" em uma etapa e volte; conclua.
5. Na tela final, "Testar a SelenIA" abre o painel no simulador.

## Histórico
- 27/09/2026: primeira versão (7 etapas, aceite das regras, conclusão
  obrigatória para abrir o painel; WhatsApp só com "Conectar depois").
- 27/09/2026: "Como a SelenIA deve falar de você" na etapa 1 (Pedro).
- 27/09/2026: rascunho de todas as etapas guardado na página até o
  "Continuar"; lixeira para remover regra extra; recuperação quando o
  cadastro já existe; bandeira do +55 desenhada (o Windows não mostra
  emoji de bandeira).
