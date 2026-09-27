# Login com Google

> Situação: funcionando; falta o Client ID do Google no `.env`. Última atualização: 27/09/2026.

## O que é

A profissional entra no painel com a conta Google, sem criar senha. No
primeiro acesso ela preenche o cadastro; depois disso, cai direto no
painel. Só entra quem foi convidado.

## Por que existe

O painel mostra trechos de conversa clínica e gasta a chave da API da
Claude. Antes do login, qualquer pessoa que soubesse o slug de uma
profissional abria o perfil, os documentos e as conversas dela.

Decisões:
- **Login com Google, não senha** (Pedro, 26/09/2026). A pessoa não cria
  mais uma senha, e a MarIA não guarda nenhuma. O Google só informa
  nome, e-mail e foto: não há acesso à agenda nem ao Gmail dela, e por
  isso o app não passa pela verificação do Google. A agenda continua
  com a conta de serviço ([configuração](../tecnico/configuracao.md)).
- **Só e-mails convidados** (proposta aceita em 26/09/2026). Sem a
  lista, qualquer conta Google criaria cadastro e usaria a MarIA.
- **Um botão só.** O protótipo tem "Entrar" e "Cadastrar" separados,
  para a apresentação; no produto, o mesmo botão serve para os dois, e
  o sistema sabe se a conta já tem cadastro.
- **Sessão no servidor**, e não um token guardado no navegador: dá para
  encerrar a sessão (sair, ou tirar alguém da lista) e o código fica num
  cookie que o JavaScript da página não consegue ler.

## Como usar

1. Abra o painel e clique em **Continuar com o Google**.
2. Escolha a conta. No primeiro acesso, você passa pelo
   [cadastro em etapas](cadastro-em-etapas.md); depois dele, cai direto
   no painel.
3. Para sair, clique em **Sair**, no topo do painel.

Se aparecer **"Acesso ainda não liberado"**, o e-mail não está na lista
de convidados.

## Como funciona

1. O botão do Google (script oficial, no navegador) devolve um token
   assinado pelo Google com quem é a pessoa.
2. O painel manda esse token para `POST /auth/google`.
3. O backend confere a assinatura, se o token foi emitido para o nosso
   Client ID, se o e-mail foi verificado pelo Google e se está em
   `ALLOWED_EMAILS`.
4. Cria ou atualiza a conta (`User`, pelo identificador permanente do
   Google) e abre uma sessão (`UserSession`): um código aleatório vai
   para o cookie `maria_session`; o banco guarda só o hash dele.
5. Toda rota de gestão exige a sessão. Dados de outra profissional
   respondem como inexistentes (404), para não confirmar que existem.
6. `GET /auth/me` diz ao painel quem está logado e se já tem cadastro.
   Sem cadastro concluído, o painel mostra o
   [cadastro em etapas](cadastro-em-etapas.md); `POST /professionals`
   cria a profissional, gera o slug a partir do nome e liga à conta.

Rotas abertas, sem login: `/health`, `/auth/config` (Client ID, que
não é segredo), `/auth/google` e `/assistant/guidelines` (regras fixas
do produto).

O painel chama a API em `/api`, no mesmo endereço dele (proxy do Vite
em desenvolvimento, do servidor web em produção). Assim o cookie é do
mesmo site e o `SameSite=Lax` funciona.

Arquivos: `services/auth.py`, `routers/auth.py`, `routers/professionals.py`
(e a checagem de dono nas outras rotas), `frontend/src/pages/Login.jsx`,
`frontend/src/pages/Onboarding.jsx`, `frontend/src/App.jsx`.

## Textos fixos

Não se aplica: nenhum texto vai para o contato. As mensagens da tela
(ex.: "Acesso ainda não liberado para este e-mail.") são do painel.

## Configuração

| Variável | Para que serve |
|---|---|
| `GOOGLE_CLIENT_ID` | Client ID do tipo "Web application" no Google Cloud. Sem ele, a tela de login avisa que não está configurado |
| `ALLOWED_EMAILS` | E-mails convidados, separados por vírgula. Vazio = ninguém entra |
| `SESSION_DAYS` | Validade da sessão. Padrão: 7 dias |
| `SESSION_COOKIE_SECURE` | `true` em produção (HTTPS) |

No Google Cloud (projeto da MarIA), uma vez só: tela de consentimento
externa em modo **teste**, com os e-mails convidados como usuários de
teste, e um cliente "Web application" com a origem
`http://localhost:5173` (em produção, o endereço do painel). Não há
URI de redirecionamento nem Client secret.

## Segurança e LGPD

- **Dados guardados da conta:** identificador do Google, e-mail, nome e
  endereço da foto. Nenhuma senha.
- **Sessão:** cookie `httpOnly` (o JavaScript não lê), `SameSite=Lax`
  (não vai em requisições de outros sites) e `Secure` em produção. O
  banco guarda o hash do código, então quem ler o banco não se passa
  pela profissional. Expira em 7 dias.
- **Quem sai da lista de convidados perde o acesso na hora**, mesmo com
  sessão aberta.
- **Tentativas de login:** no máximo 10 a cada 5 minutos por IP.
- **Isolamento:** cada rota confere se o dado é da profissional logada.

## Limitações e pendências

- Falta o `GOOGLE_CLIENT_ID` (D9 do plano). Por enquanto só o Pedro
  está convidado; a Marília entra quando o painel estiver pronto
  (decisão de 27/09/2026).
- Depois de 09/10 (fora do MVP): trocar a lista do `.env` por
  **cadastro com aprovação**
  (qualquer pessoa se cadastra e a conta fica aguardando liberação) e
  publicar o app no Google. Cadastro aberto, sem aprovação, só com
  cobrança e verificação do profissional.
- O limite de tentativas vale para um processo só; com mais de um, a
  contagem precisa ser compartilhada.
- Em modo de teste do Google, só os usuários de teste conseguem entrar.
  Para abrir a mais pessoas, o app precisa ser publicado no Google
  (sem verificação, porque só usa nome, e-mail e foto).
- Sem papéis nem mais de um usuário por profissional.

## Como testar

Automático: `tests/test_auth.py` (rotas fechadas sem login, primeiro
acesso e cadastro, convite, token inválido, e-mail não verificado,
perda de acesso ao sair da lista, isolamento entre profissionais,
limite de tentativas). Os outros testes rodam com uma conta de teste
dona de tudo (`conftest.py`).

Manual:
1. Rode `iniciar.bat` (ou suba o backend e o painel à mão e abra
   `http://localhost:5173/?sair`). O `?sair` encerra a sessão salva no
   navegador, para o teste começar pela tela de login.
2. Entre com um e-mail convidado: primeiro acesso abre o cadastro em
   etapas; conclua e chegue ao painel.
3. Clique em **Sair** e entre de novo: vai direto ao painel.
4. Entre com um e-mail fora da lista: aparece "Acesso ainda não
   liberado".

## Histórico
- 27/09/2026: primeira versão (login, lista de convidados, sessões,
  proteção das rotas, primeira etapa do cadastro).
- 27/09/2026: `?sair` no endereço encerra a sessão (usado pelo
  `iniciar.bat`); por enquanto só o e-mail de teste do Pedro está
  convidado.
