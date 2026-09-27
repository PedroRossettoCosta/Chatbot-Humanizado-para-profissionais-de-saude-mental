# Atendimento pelo WhatsApp

> Situação: funcionando até a Meta; falta publicar o app para chegarem mensagens reais. Última atualização: 27/09/2026.

## O que é

A MarIA recebe e responde mensagens de verdade no WhatsApp, pelo número
dedicado da profissional. A Meta avisa o sistema a cada mensagem (o
**webhook**); a MarIA faz a triagem, responde pela API da Meta, e a
conversa aparece em [Conversas](conversas.md). O que a profissional
escreve no painel também chega no WhatsApp da pessoa.

## Por que existe

- É o canal do produto: o simulador serve para testar, mas as pessoas
  procuram a profissional pelo WhatsApp.
- O plano do MVP (sexta 02/10) previa o webhook por túnel temporário,
  porque o MVP roda no notebook (decisão de 25/09/2026, sem deploy). Foi
  feito em 27/09/2026, adiantado.
- **Endereço fixo** (Pedro, 27/09/2026): em vez de um túnel com endereço
  novo a cada vez, o ngrok gratuito com domínio fixo. O endereço é
  cadastrado uma vez só na Meta.
- **Espera antes de responder** (Pedro, 27/09/2026): a API do WhatsApp
  não avisa quando a pessoa está digitando. A MarIA espera alguns
  segundos depois de cada mensagem, junta as mensagens quebradas e
  responde uma vez, mostrando "digitando…" enquanto isso.
- **Avisos de entregue e lido ficam fora do MVP** (27/09/2026): a tela
  não mostra ✓✓.

## Como usar

Para a profissional, nada muda: as conversas do WhatsApp aparecem em
Conversas (sem a etiqueta "Teste"), e ela responde por lá.

Para subir o sistema com o WhatsApp (Windows): `iniciar.bat` abre o
túnel do ngrok numa janela própria ("MarIA - Tunel"), além da API e do
painel. Configuração inicial, uma vez só:

1. Conta no ngrok (gratuita), domínio fixo em **Domains** e o
   authtoken instalado (`ngrok config add-authtoken ...`).
2. No `backend/.env`: `WHATSAPP_APP_SECRET`, `WHATSAPP_VERIFY_TOKEN` e
   `PUBLIC_WEBHOOK_HOST` (ver [configuração](../tecnico/configuracao.md)).
3. Na Meta, caso de uso do WhatsApp → **Etapa 2. Configuração da
   produção** → **Configurar webhooks**: URL de callback
   `https://{PUBLIC_WEBHOOK_HOST}/webhook/whatsapp` e o mesmo verify
   token; **Verificar e salvar**; ligar **Assinar webhooks** da conta.
4. O número da profissional precisa estar ligado a ela
   (`professionals.whatsapp_phone_number_id`). Até o "adicionar número
   pelo painel" (05/10), isso é feito direto no banco.

## Como funciona

Cada chamada da Meta (`POST /webhook/whatsapp`):

1. **Assinatura:** o sistema confere o `X-Hub-Signature-256` (HMAC do
   corpo com o App Secret). Sem assinatura válida, ou sem segredo
   configurado, responde 401 e não grava nada.
2. **Responde "recebi" na hora** e processa em segundo plano, porque a
   Meta reenvia o que demora.
3. **Para cada mensagem** (`services/whatsapp_inbox.py`):
   - descobre a profissional pelo número que recebeu
     (`phone_number_id`); número sem profissional é ignorado;
   - descarta reenvio da Meta (o mesmo `wamid` já gravado);
   - mostra "digitando…" para a pessoa (e marca como lida);
   - grava e roda a **triagem na hora** (`services/pipeline.py`, o mesmo
     caminho do simulador). Aviso de IA na primeira mensagem e
     mensagem de emergência saem imediatamente;
   - a resposta normal espera `REPLY_DEBOUNCE_SECONDS` (6 s), e a espera
     recomeça se chegar outra mensagem. Depois, as mensagens da pessoa
     desde a última resposta viram um texto só, que passa pelo handoff
     ou pela MarIA;
   - áudio, imagem e outros tipos ficam na conversa como "[Áudio]",
     "[Imagem]" etc., sem triagem (não há texto), e a pessoa recebe um
     aviso fixo.
4. Avisos de entregue e lido, reações e os outros campos assinados são
   ignorados.

Resposta da profissional pelo painel numa conversa do WhatsApp: sai
primeiro pela API da Meta e só é gravada se a Meta aceitar; se não,
a tela mostra "Não consegui enviar pelo WhatsApp agora" (502).

O **túnel** expõe o backend na internet, mas um filtro em `main.py`
só deixa passar `/webhook/` quando a chamada chega pelo
`PUBLIC_WEBHOOK_HOST`; o resto da API responde 404 por ali e continua
acessível só na máquina.

O `GET /webhook/whatsapp` responde o desafio da Meta quando o
`hub.verify_token` bate com `WHATSAPP_VERIFY_TOKEN`.

Arquivos: `routers/webhook.py`, `services/whatsapp.py` (assinatura,
leitura do formato da Meta, envio, "digitando…"),
`services/whatsapp_inbox.py` (ordem, espera, tipos não suportados),
`services/pipeline.py`, `routers/conversations.py` (resposta do
painel), `main.py` (filtro do túnel), `iniciar.bat`.

## Textos fixos

| Constante | Texto | Aprovado pela Marília? |
|---|---|---|
| `whatsapp_inbox.UNSUPPORTED_MESSAGE` | "Por enquanto só consigo ler mensagens de texto. Pode me escrever o que você precisa?" | Não |

Os outros textos (aviso de IA, emergência, handoff) são os mesmos do
simulador.

## Configuração

`WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_APP_SECRET`, `WHATSAPP_VERIFY_TOKEN`,
`WHATSAPP_API_VERSION`, `PUBLIC_WEBHOOK_HOST`, `REPLY_DEBOUNCE_SECONDS`
([configuração](../tecnico/configuracao.md)). Campo da profissional:
`whatsapp_phone_number_id`.

## Segurança e LGPD

- **Assinatura obrigatória** em toda mensagem; sem App Secret, nada
  entra (falha fechada). Sem isso, qualquer pessoa que descobrisse o
  endereço poderia injetar mensagens, inclusive uma falsa emergência.
- **Só o webhook pelo túnel**: as rotas do painel não respondem pelo
  endereço público.
- Número e nome do contato ficam cifrados, como no simulador. Nenhum
  conteúdo de mensagem vai para os logs; só tipos, ids e códigos de
  erro da Meta.
- O `wamid` de cada mensagem recebida é único no banco: um reenvio da
  Meta nunca gera duas respostas.

## Limitações e pendências

- **O app da Meta precisa ser publicado** para chegarem mensagens
  reais; antes disso, só os testes do painel da Meta. Publicar pede um
  link público de política de privacidade.
- **Sistema desligado = MarIA fora do ar:** com o notebook ou o túnel
  desligados, ninguém recebe resposta, nem a mensagem de emergência. A
  Meta tenta reenviar por um tempo, e as mensagens chegam atrasadas
  quando o sistema volta. Em produção, o backend rodaria num servidor
  ligado o tempo todo.
- As esperas ficam na memória: se o backend reiniciar durante uma, a
  resposta daquela rajada não sai (a triagem já rodou).
- Falha ao enviar uma mensagem da MarIA (inclusive a de emergência) só
  vai para o log; sem avisos de entrega, o painel não mostra.
- Só texto: áudio, imagem e documento não são lidos nem triados.
- O número da profissional é ligado no banco à mão até 05/10.
- Conta Meta sem verificação: no máximo 2 números. Em produção, cada
  profissional conectaria o número na própria conta (programa de
  Provedor de Tecnologia), sem esse limite.
- O texto de tipo não suportado precisa da aprovação da Marília.

## Como testar

Automático: `tests/test_webhook.py` (desafio, assinatura, mensagem com
aviso de IA e resposta, reenvio, número sem profissional, emergência na
hora, áudio, avisos de status, mensagens quebradas juntas, espera
recomeçada com uma resposta só, resposta do painel pelo WhatsApp e
recusada pela Meta, filtro do túnel). Nenhum teste chama a Meta:
`conftest.py` substitui o envio.

Manual:
1. Com `iniciar.bat` rodando, no painel da Meta → Webhooks → Whatsapp
   Business Account → campo **messages** → **Teste** → **Enviar para
   servidor**. A janela do túnel mostra `POST /webhook/whatsapp 200`
   (401 = App Secret errado). Feito em 27/09/2026: 200.
2. Com o app publicado: mande "oi" de outro celular para o número da
   MarIA; chegam o aviso de IA e a resposta, e a conversa aparece em
   Conversas. Mande "eu to pensando" e "em me matar" em seguida: sai a
   mensagem de emergência e o alerta.

## Histórico

- 27/09/2026: webhook, espera antes de responder, envio pela API da
  Meta, resposta do painel pelo WhatsApp, túnel fixo com filtro.
