# MarIA — Descrição da Aplicação Final (Web e Mobile)

> Documento de referência para prototipagem (usado com o Google Stitch).
> Descreve a visão do produto final, não apenas o que já está
> implementado no MVP atual.

---

## 1. Site público / Contratação (WEB)

**Fluxo completo de acesso:**

```
Visitante chega no site
   ↓
Landing page pública (sem login)
   ↓
Clica em "Entrar" ou "Começar agora"
   ↓
Login / Cadastro
   ↓
Sistema verifica: essa profissional já tem uma assinatura ativa?
   ├── SIM → vai direto pro Dashboard (painel completo)
   └── NÃO → vai pra página de Planos/Contratação
```

**Telas:**

1. **Landing Page (pública, institucional)**
   - Hero: proposta de valor clara — "Atendimento inicial humanizado,
     automatizado por IA, para profissionais de saúde mental"
   - Seção de como funciona (3 passos: configure seu assistente →
     conecte seu WhatsApp → seus pacientes são atendidos 24h)
   - Seção dos 3 módulos (Customização/RAG, Administrativo/Agenda,
     Triagem de Segurança) — como benefícios, não como jargão técnico
   - Depoimento ou caso de uso
   - Seção de planos/preços (resumida, com CTA "Ver planos completos")
   - Rodapé com links institucionais (termos de uso, política de
     privacidade/LGPD, contato)
   - Botão fixo no header: "Entrar" e "Começar agora"

2. **Login** — e-mail/senha (ou login social), "Esqueci minha senha",
   link para cadastro.

3. **Cadastro** — nome, e-mail, senha, especialidade/profissão
   (opcional), aceite dos termos (LGPD). Após cadastrar, vai direto
   pra tela de Planos (ainda sem assinatura ativa).

4. **Planos / Contratação** (mostrada sempre que o profissional logado
   NÃO tem assinatura ativa)
   - Cards comparando planos (ex: Básico — 1 canal, X mensagens/mês;
     Profissional — todos os canais, mensagens ilimitadas, agenda +
     pagamentos; Premium — tudo + prioridade de suporte)
   - Preço mensal, recursos inclusos, botão "Assinar"
   - Formulário de pagamento (cartão ou PIX) — pensar em Stripe como
     processador
   - Após pagamento confirmado: redireciona pro Onboarding (conectar
     WhatsApp, subir primeiro documento, configurar tom de voz) e
     depois pro Dashboard

5. **Estado "assinatura inativa/vencida"** — ao logar, cai numa tela
   avisando que a assinatura está inativa, com botão pra reativar; não
   perde dados (documentos/configurações continuam salvos, só o
   assistente fica pausado).

**Comportamento do header:** visitante não-logado vê "Entrar / Começar
agora"; profissional logada sem plano vê o nome dela + "Ver planos";
profissional logada com plano ativo vê o painel normal.

---

## 2. Painel do Profissional (WEB, logado e com assinatura ativa)

**O que é:** Painel administrativo para a profissional gerenciar o
assistente MarIA — configuração, conversas, agenda, pagamentos e
alertas de segurança.

**Usuário-alvo:** A própria profissional. Uso principal em
desktop/laptop, responsivo.

**Tom visual:** Acolhedor, calmo e profissional — nunca clínico/frio
nem corporativo genérico. Paleta suave (azul-petróleo, verde-sálvia,
bege/off-white), bastante espaço em branco, tipografia legível.
Exceção proposital: a seção de alertas de segurança se destaca
visualmente (cor de alerta) para nunca passar despercebida. Idioma:
português (Brasil).

**Navegação (menu lateral):**

1. **Início / Dashboard** — mensagens recebidas hoje, novos leads,
   taxa de conversão, próximos agendamentos, alertas de segurança
   recentes em destaque.
2. **Conversas** — inbox por canal (WhatsApp/Instagram/TikTok), busca
   e filtro ("novo lead", "aguardando resposta", "sinalizado"),
   histórico completo estilo chat com indicação clara de mensagens do
   bot vs. escaladas para humano.
3. **Base de Conhecimento** — lista de documentos enviados, upload
   (PDF/DOCX/TXT/MD), preview de conteúdo, remoção.
4. **Configuração do Assistente** — nome do bot, tom de voz, mensagens
   padrão (saudação, indisponibilidade, encaminhamento de emergência),
   preview ao vivo.
5. **Agenda** — calendário integrado ao Google Calendar, pré-
   agendamentos pendentes de confirmação (aprovar/recusar).
6. **Pagamentos** — comprovantes de PIX enviados, status (validado
   automaticamente por visão computacional / pendente / rejeitado),
   valor detectado vs. esperado.
7. **Alertas de Segurança** — trecho da conversa que disparou o
   alerta, horário, canal, status (novo/revisado), botão "marcar como
   revisado". Design mais sério/urgente que o resto do painel.
8. **Configurações da Conta** — perfil, canais conectados, política de
   retenção de dados, exportar/excluir dados (LGPD), plano/assinatura.

**Elementos recorrentes:** indicador de "assistente ativo/pausado"
(a profissional pode assumir a conversa manualmente a qualquer
momento); notificação em tempo real de novo alerta; lembrete discreto
do princípio ético central — o assistente nunca diagnostica nem
substitui atendimento clínico.

---

## 3. App MarIA (MOBILE — iOS/Android)

**Plataforma: aplicativo mobile.** Complementar ao painel web — não
inclui contratação/assinatura (isso é só web); destinado apenas a
profissionais já assinantes ativas.

**O que é:** Um app companion focado em monitoramento rápido e
resposta a urgências — versão enxuta pra acompanhar o essencial pelo
celular, especialmente fora do consultório.

**Usuário-alvo:** A profissional, em trânsito ou fora do horário de
trabalho. Prioridade máxima: nunca perder um alerta de segurança.

**Tom visual:** Mesma identidade da web, adaptada pra tela pequena —
cards grandes, poucos elementos por tela, ações principais a um toque
de distância. Área de alertas de segurança sempre em destaque.

**Login:** e-mail/senha (ou social), sem cadastro/planos — conta sem
assinatura ativa mostra uma tela informando que é preciso ativar pelo
site, com link pra versão web.

**Navegação (barra inferior, 4 abas):**

1. **Início** — agenda de hoje, novas mensagens, alertas de segurança
   pendentes em destaque máximo no topo, com notificação push
   imediata (mesmo com o app fechado, som/vibração distintos).
2. **Conversas** — inbox simplificado por canal, responder
   manualmente ou pausar o assistente direto do celular.
3. **Agenda** — visualização do dia/semana, aprovar/recusar pré-
   agendamentos com um toque.
4. **Alertas** — histórico de alertas de segurança: trecho da
   conversa, horário, canal, status; ação rápida "ligar para o CVV
   (188)" e "marcar como revisado".

**Funcionalidades mobile-específicas:**
- Notificações push: alerta de segurança (prioridade alta), novo lead
  quente, agendamento confirmado, pagamento pendente de revisão.
- Upload rápido de documento por câmera (foto + OCR).
- Modo "fora do expediente" — toggle rápido pra pausar o assistente.
- Widget de tela inicial (opcional) com contagem de mensagens novas e
  status de alertas.

**O que NÃO existe no mobile** (fica só na web, de propósito): landing
page/marketing, cadastro, planos/pagamento de assinatura, configuração
completa do assistente, tela de pagamentos/PIX detalhada.
