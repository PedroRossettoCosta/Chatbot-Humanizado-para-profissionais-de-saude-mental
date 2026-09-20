# Explicação — Protótipos Stitch (Web + Mobile) e Pesquisa de PWA

> Documento de leitura, gerado a partir da análise dos protótipos em
> `Documentation/TCC App Design/` e dos docs de planejamento já
> existentes. Não implementa nada — é só entendimento e opinião, pra
> discutir com o orientador.

---

## 1. Sua leitura do web vs. mobile — já está escrita e bate

Não é só uma ideia sua: já existe um documento
(`descricao-app-web-mobile.md`, na mesma pasta) descrevendo
exatamente essa divisão.

- **Web = produto completo**
  Landing page pública, cadastro, planos/assinatura (Stripe), painel
  com 8 seções: Dashboard, Conversas, Base de Conhecimento,
  Configuração do Assistente, Agenda, Pagamentos/PIX, Alertas de
  Segurança, Configurações da Conta.

- **Mobile = companion**
  Só para quem já é assinante (sem cadastro/planos/pagamento) — 4
  abas: Início, Conversas, Agenda, Alertas. Foco em nunca perder um
  alerta de segurança, com notificação push, upload por câmera (OCR)
  e um toggle rápido de "fora do expediente".

**Conclusão:** seu instinto está alinhado com o que já foi combinado.
Não é preciso reabrir essa decisão com o orientador — só confirmar
que "companion" quer dizer exatamente esse escopo.

---

## 2. O que tem dentro de `Documentation/TCC App Design`

É um export do **Stitch** (ferramenta de design da Google — gera UI a
partir de prompt, já em Tailwind). Cada tela vem em uma pasta assim:

```
nome_da_tela/
├── code.html   → HTML autocontido, Tailwind via CDN, sem framework
└── screen.png  → screenshot da tela
```

Além disso, cada produto tem um `DESIGN.md` com o design system em
YAML (cores, tipografia, espaçamento) + um texto explicando a
filosofia visual.

### Dois produtos, telas separadas

**`stitch_painel_chatbot_sa_de_mental_web/`** — 8 telas:
landing, login/cadastro, dashboard, conversas multicanal, alertas de
segurança, planos/contratação, assinatura inativa, e uma tela extra
("clinical intake triage platform").

**`stitch_psicompanion_mobile_app/`** — 4 telas:
início, agenda, conversas, alertas de segurança.

Isso bate com a divisão de 8 seções (web) vs. 4 abas (mobile) do
documento de planejamento.

### Como é o design, na prática

Abri o `code.html` do dashboard web e da tela inicial mobile pra ver
de verdade. Características:

- **Estilo geral:** "Organic Warm Minimalism" — cantos bem
  arredondados (`rounded-xl` / `rounded-2xl`), tons quentes de
  bege/off-white, verde-petróleo/sálvia como cor primária, sombras
  suaves e difusas (nunca preto puro), uma única fonte:
  **Plus Jakarta Sans**.

- **Alertas de segurança são tratados como cidadão de primeira
  classe** — cor de crise (vermelho-coral), sempre com borda lateral
  sólida + fundo tingido, sempre com botão de ligação direta pro CVV
  (`tel:188`), sempre em destaque máximo no topo da tela. Isso é
  consistente nos dois produtos, não é um alerta genérico qualquer.

- **Layout web:** sidebar fixa (288px) + header fixo + conteúdo em
  grid de 12 colunas (ex: conversas ocupam 7/12, agenda 5/12).

- **Layout mobile:** header fixo + bottom nav de 4 abas fixa, cards
  full-width, alvos de toque ≥48px — pensado pra uso com uma mão.

- Cada `code.html` é **estático e autocontido** — HTML + config do
  Tailwind inline + um pouco de JS vanilla pra interações simples
  (toggle, modal). Não tem roteamento, não tem estado real, não
  conversa com nenhuma API. É referência **visual e de UX**, não
  código pronto pra reaproveitar direto no React.

### Uma inconsistência que vale resolver com o orientador

O produto aparece com **três nomes diferentes** dentro do próprio
protótipo:

| Nome | Onde aparece |
|---|---|
| **MarIA** | Nome oficial (já registrado no seu material de projeto); aparece no sidebar do dashboard web e em algumas telas |
| **Serenia** | Nome de várias pastas/telas web (`serenia_dashboard_principal`, `serenia_login_cadastro`...) e no texto do design system web ("IA Serenia") |
| **Serena Clínico** | Nome do app mobile inteiro, incluindo o design system (`serena_cl_nico/DESIGN.md`) |

Parece que o Stitch foi rodado em sessões diferentes e o nome foi
variando (ou era um teste de naming). Vale bater o martelo antes de
implementar — senão a inconsistência se espalha pelo código
(componentes, variáveis, textos de tela) e fica mais caro de corrigir
depois.

**Divergência menor:** o `README.md` da pasta descreve o mobile como
tendo abas *Agenda, Pacientes, Alertas, Perfil*, mas as telas que de
fato existem (e o código delas) usam *Início, Conversas, Agenda,
Alertas* — que é o que bate com `descricao-app-web-mobile.md`. O
`README.md` parece desatualizado nesse ponto; eu confiaria nas telas
e no doc de planejamento.

---

## 3. Pesquisa de tecnologias para o PWA

Contexto que usei pra pesquisar:

- o backend já é **FastAPI (Python)**;
- o frontend já é **React + Vite** (ainda simples — sem TypeScript,
  sem router, sem UI kit, confirmado no `package.json`);
- o requisito não-negociável do mobile é **nunca perder um alerta de
  segurança** (ou seja, notificação push confiável é obrigatória).

### Resposta curta: não precisa de linguagem nova

Um **PWA** (Progressive Web App) não é uma stack separada — é o
mesmo app web (HTML/CSS/JS, React no seu caso) ganhando um punhado de
APIs de navegador que o deixam instalável e capaz de rodar código em
segundo plano.

| Peça | Tecnologia | Pra que serve |
|---|---|---|
| Instalabilidade | **Web App Manifest** (`manifest.json`) | Ícone na tela inicial, splash screen, modo standalone (sem barra de navegador) |
| Service Worker | **Workbox**, via `vite-plugin-pwa` (se integra direto no seu Vite atual) | Cache de assets, funcionamento offline básico, escuta eventos de push |
| Notificações push | **Push API** + **Notification API** (do navegador) + backend enviando via **web-push** (protocolo VAPID) | O alerta de segurança chegar mesmo com o app fechado |
| Linguagem | Continua **JavaScript/React** — dá pra migrar pra **TypeScript** conforme o projeto cresce (recomendo, não é urgente) | Sem necessidade de Swift/Kotlin/Dart |

### O ponto de atenção real: push notification no iOS

Essa é a única limitação técnica que pode furar o requisito "nunca
perder um alerta":

- **Android/Chrome:** push funciona bem em PWA instalado, inclusive
  com o app fechado.
- **iOS/Safari:** só a partir do **iOS 16.4** (2023) o Safari permite
  push notifications — e **só se o PWA estiver instalado na tela
  inicial** (não funciona numa aba normal do Safari). A profissional
  precisa instalar o app manualmente uma vez.

Isso é relevante o bastante pra virar uma linha na seção de
limitações do TCC — igual ao que vocês já fizeram com a restrição do
WhatsApp Brasil/EUA.

### PWA vs. nativo (React Native / Capacitor) — por que PWA ganha aqui

- **Um único código-fonte** cobre web completo e mobile companion
  (mesmos componentes de UI, mesmo design system dos dois
  `DESIGN.md`), sem duplicar lógica em duas linguagens.
- **Sem app store:** nada de esperar aprovação da Apple/Google, nada
  de conta de desenvolvedor paga (Apple cobra US$99/ano) — importante
  pro cronograma de um TCC com defesa marcada.
- **Deploy é só publicar a URL** — a profissional acessa o link, o
  navegador oferece "instalar".
- **Reaproveita 100% do investimento** já feito no design system web
  (cores, tipografia, componentes) — o "companion" mobile não é um
  app do zero, é uma casca PWA enxuta usando a mesma linguagem
  visual.

O custo real é só a limitação de push no iOS — existe, mas é
contornável (ex: fallback de e-mail/SMS pra alerta crítico, ou
simplesmente documentar como limitação conhecida).

---

## 4. Minha opinião, resumida

1. **A divisão web/mobile está certa e já documentada.** Só
   confirmar com o orientador que "companion" é mesmo esse escopo.
2. **PWA é a escolha certa** pra esse projeto — dado o prazo de TCC,
   o frontend já ser React/Vite, e web/mobile compartilharem o mesmo
   design system. Um app nativo separado seria desperdício de tempo
   pra uma feature que é essencialmente "ver alertas e responder
   rápido".
3. **Antes de implementar, resolver o nome** (MarIA vs. Serenia vs.
   Serena Clínico) — barato agora, caro depois de já ter componente
   React chamado `SereniaSidebar` espalhado pelo código.
4. Os `code.html` do Stitch são ótima referência de **visual e
   hierarquia de informação**, mas são protótipos estáticos,
   desconectados do FastAPI. A implementação real vai ser reconstruir
   esses componentes em React (Tailwind de verdade, não CDN)
   consumindo os endpoints que já existem em
   `backend/app/routers/`.
