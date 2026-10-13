// As 7 etapas do cadastro (protótipo: telas C1 a C9). Cada etapa recebe
// `save(campos, próximaEtapa)`, que grava no backend e avança.

import { useState } from "react";

import { Button, ErrorBox, Field, formatDateTime, inputClass } from "../../components/ui.jsx";

// Rascunho do cadastro: o que foi digitado e ainda não passou pelo
// "Continuar". Fica no componente do cadastro (e não em cada etapa), para
// não se perder quando a pessoa vai e volta entre as etapas. O banco só
// recebe no "Continuar".
function useDraft(drafts, setDraft, key, fallback) {
  return [drafts[key] ?? fallback, (value) => setDraft(key, value)];
}

export const STEPS = ["Seus dados", "Atendimento", "Tom de voz", "Regras", "Regras extras", "WhatsApp", "Revisão"];

function StepHeader({ eyebrow, title, children }) {
  return (
    <div>
      <p className="text-xs font-semibold tracking-wider text-primary">{eyebrow}</p>
      <h1 className="mt-2 text-3xl font-bold tracking-tight text-ink">{title}</h1>
      <p className="mt-3 text-base leading-relaxed text-muted">{children}</p>
    </div>
  );
}

function StepFooter({ step, onBack, children }) {
  return (
    <div className="mt-10 flex flex-wrap items-center justify-between gap-4 border-t border-line pt-6">
      {onBack ? (
        <Button variant="soft" onClick={onBack}>
          ← Voltar
        </Button>
      ) : (
        <span />
      )}
      <p className="order-last w-full text-center text-sm text-muted sm:order-none sm:w-auto">
        Etapa {step} de 7 · Seu progresso é salvo automaticamente
      </p>
      <div className="flex items-center gap-3">{children}</div>
    </div>
  );
}

// Etapa 1 — Seus dados (C1)
export function StepData({ professional, me, guidelines, drafts, setDraft, save, busy, error }) {
  const [name, setName] = useDraft(drafts, setDraft, "name", professional?.name || me.name || "");
  const [alertEmail, setAlertEmail] = useDraft(drafts, setDraft, "alert_email", professional?.alert_email || me.email);
  const [pronouns, setPronouns] = useDraft(drafts, setDraft, "pronouns", professional?.pronouns || "");

  function submit(event) {
    event.preventDefault();
    save({ name: name.trim(), alert_email: alertEmail.trim(), pronouns }, 2);
  }

  return (
    <form onSubmit={submit}>
      <StepHeader eyebrow="ETAPA INICIAL" title="Vamos começar pelo básico">
        Estas informações identificam você para as pessoas que procuram atendimento e definem para onde enviamos os
        avisos importantes.
      </StepHeader>
      <div className="mt-8 space-y-6">
        <Field label="Nome de exibição" required hint="É como a SelenIA vai se referir a você nas conversas.">
          <input className={inputClass} value={name} onChange={(e) => setName(e.target.value)} required maxLength={255} />
        </Field>
        <Field
          label="Como a SelenIA deve falar de você"
          required
          hint="É assim que ela se refere a você nas conversas com as pessoas. Ex.: “Ela atende online”, “Ele atende online” ou, no neutro, só pelo nome."
        >
          <select
            className={`${inputClass} cursor-pointer`}
            value={pronouns}
            onChange={(e) => setPronouns(e.target.value)}
            required
          >
            <option value="" disabled>
              Escolha uma opção
            </option>
            {guidelines.pronoun_options.map((option) => (
              <option key={option.key} value={option.key}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>
        <Field
          label="E-mail para alertas"
          required
          hint="Para onde enviamos os avisos de emergência. Por segurança, o e-mail não inclui o conteúdo da conversa."
        >
          <input
            className={inputClass}
            type="email"
            value={alertEmail}
            onChange={(e) => setAlertEmail(e.target.value)}
            required
          />
        </Field>
        <ErrorBox>{error}</ErrorBox>
      </div>
      <StepFooter step={1}>
        <Button type="submit" disabled={busy || !name.trim() || !alertEmail.trim() || !pronouns}>
          {busy ? "Salvando..." : "Continuar →"}
        </Button>
      </StepFooter>
    </form>
  );
}

// Etapa 2 — Seu atendimento (C2)
export function StepService({ professional, drafts, setDraft, save, goTo, busy, error }) {
  const [audience, setAudience] = useDraft(drafts, setDraft, "audience_description", professional.audience_description || "");
  const [serviceInfo, setServiceInfo] = useDraft(drafts, setDraft, "service_info", professional.service_info || "");
  const [minutes, setMinutes] = useDraft(
    drafts,
    setDraft,
    "session_minutes",
    professional.session_minutes ? String(professional.session_minutes) : ""
  );

  const minutesNumber = Number(minutes);
  const validMinutes = Number.isInteger(minutesNumber) && minutesNumber >= 15 && minutesNumber <= 240;

  function submit(event) {
    event.preventDefault();
    save({ audience_description: audience.trim(), service_info: serviceInfo.trim(), session_minutes: minutesNumber }, 3);
  }

  return (
    <form onSubmit={submit}>
      <StepHeader eyebrow="SEU ATENDIMENTO" title="Conte como é o seu atendimento">
        A SelenIA usa estas informações para apresentar você e responder dúvidas práticas. Escreva como você explicaria
        para alguém que chega pela primeira vez.
      </StepHeader>
      <div className="mt-8 space-y-6">
        <Field label="Especialidade e público" required>
          <textarea
            className={`${inputClass} min-h-28`}
            value={audience}
            onChange={(e) => setAudience(e.target.value)}
            placeholder="Ex.: psicanalista; atendo adultos em sofrimento por relacionamentos (término, traição, dependência emocional)"
            required
          />
        </Field>
        <Field
          label="Informações do serviço"
          required
          hint="Inclua modalidade, frequência, valor e forma de pagamento. A SelenIA informa o valor já na primeira pergunta sobre preço."
        >
          <textarea
            className={`${inputClass} min-h-28`}
            value={serviceInfo}
            onChange={(e) => setServiceInfo(e.target.value)}
            placeholder="Ex.: online pelo Google Meet, sessões semanais, R$ 200 por sessão, pagamento no Pix"
            required
          />
        </Field>
        <Field label="Duração da sessão (minutos)" required hint="Usada pela agenda para oferecer horários.">
          <div className="flex items-center gap-3">
            <input
              className={`${inputClass} max-w-32`}
              type="number"
              min={15}
              max={240}
              value={minutes}
              onChange={(e) => setMinutes(e.target.value)}
              placeholder="50"
              required
            />
            <span className="mt-2 text-muted">min</span>
          </div>
        </Field>
        <ErrorBox>{error}</ErrorBox>
      </div>
      <StepFooter step={2} onBack={() => goTo(1)}>
        <Button type="submit" disabled={busy || !audience.trim() || !serviceInfo.trim() || !validMinutes}>
          {busy ? "Salvando..." : "Continuar →"}
        </Button>
      </StepFooter>
    </form>
  );
}

// Etapa 3 — Tom de voz (C3)
export function StepVoice({ professional, guidelines, drafts, setDraft, save, goTo, busy, error }) {
  const [tone, setTone] = useDraft(drafts, setDraft, "voice_tone", professional.voice_tone || "");
  const [examples, setExamples] = useDraft(drafts, setDraft, "voice_examples", professional.voice_examples || {});
  const [openExample, setOpenExample] = useState(null);

  function setExample(key, field, value) {
    setExamples({ ...examples, [key]: { ...examples[key], [field]: value } });
  }

  const complete =
    tone.trim() &&
    guidelines.voice_questions.every((q) => examples[q.key]?.good?.trim() && examples[q.key]?.bad?.trim());

  function submit(event) {
    event.preventDefault();
    save({ voice_tone: tone.trim(), voice_examples: examples }, 4);
  }

  return (
    <form onSubmit={submit}>
      <StepHeader eyebrow="PERSONALIZAÇÃO DO DIÁLOGO" title="Como a SelenIA deve soar">
        A SelenIA fala em seu nome, então precisa soar como você. Descreva o tom e mostre como você responderia, e como
        não responderia.
      </StepHeader>
      <div className="mt-6 rounded-2xl bg-primary-soft px-5 py-4 text-sm text-slate">
        <strong className="text-primary">A resposta ruim ensina tanto quanto a boa:</strong> mostra à SelenIA o que evitar.
      </div>
      <div className="mt-8 space-y-6">
        <Field label="Tom de voz" required hint="Adjetivos e diretrizes que resumem o seu jeito de conversar.">
          <input
            className={inputClass}
            value={tone}
            onChange={(e) => setTone(e.target.value)}
            placeholder="Ex.: acolhedor, direto, sem jargões"
            required
          />
        </Field>

        {guidelines.voice_questions.map((q, index) => (
          <div key={q.key} className="rounded-3xl bg-[#eff4ff] p-5">
            <p className="m-0 font-semibold text-ink">
              <span className="mr-2 inline-flex h-6 w-6 items-center justify-center rounded-full bg-white text-xs text-muted">
                {index + 1}
              </span>
              “{q.question}”
            </p>
            {q.example_good && (
              <button
                type="button"
                onClick={() => setOpenExample(openExample === q.key ? null : q.key)}
                className="mt-3 cursor-pointer border-0 bg-transparent p-0 text-sm font-semibold text-primary hover:underline"
              >
                {openExample === q.key ? "Esconder exemplo" : "Ver um exemplo"}
              </button>
            )}
            {openExample === q.key && (
              <div className="mt-3 space-y-2 rounded-2xl bg-white p-4 text-sm">
                <p>
                  <span className="font-semibold text-primary">Boa:</span> {q.example_good}
                </p>
                <p>
                  <span className="font-semibold text-danger">Ruim:</span> {q.example_bad}
                </p>
              </div>
            )}
            <div className="mt-4 grid gap-4 md:grid-cols-2 [&>*]:min-w-0">
              <Field label="✓ Resposta boa" required>
                <textarea
                  className={`${inputClass} min-h-24`}
                  value={examples[q.key]?.good || ""}
                  onChange={(e) => setExample(q.key, "good", e.target.value)}
                  placeholder="Escreva como você responderia..."
                />
              </Field>
              <Field label="✕ Resposta ruim" required>
                <textarea
                  className={`${inputClass} min-h-24`}
                  value={examples[q.key]?.bad || ""}
                  onChange={(e) => setExample(q.key, "bad", e.target.value)}
                  placeholder="Escreva uma resposta que você não quer que a SelenIA dê..."
                />
              </Field>
            </div>
          </div>
        ))}
        <ErrorBox>{error}</ErrorBox>
      </div>
      <StepFooter step={3} onBack={() => goTo(2)}>
        <Button type="submit" disabled={busy || !complete}>
          {busy ? "Salvando..." : "Continuar →"}
        </Button>
      </StepFooter>
    </form>
  );
}

// Etapa 4 — Regras da SelenIA (C4)
export function StepRules({ professional, guidelines, drafts, setDraft, acceptRules, goTo, busy, error }) {
  const alreadyAccepted = Boolean(professional.rules_accepted_at);
  const [checked, setChecked] = useDraft(drafts, setDraft, "rules_checked", alreadyAccepted);

  return (
    <div>
      <StepHeader eyebrow="SEGURANÇA FUNDAMENTAL" title="Regras que valem para todo atendimento">
        Regras de segurança iguais em todas as contas da SelenIA. Elas protegem você e as pessoas que procuram
        atendimento, e não podem ser alteradas.
      </StepHeader>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <section className="rounded-3xl bg-[#eff4ff] p-6">
          <h2 className="m-0 text-lg font-semibold text-ink">🔒 A SelenIA nunca diz</h2>
          <p className="mt-1 text-sm text-muted">Limites iguais em todas as contas da SelenIA</p>
          <ol className="mt-5 space-y-3 p-0">
            {guidelines.never_say.map((rule, index) => (
              <li key={rule} className="flex list-none gap-3 text-sm leading-relaxed text-slate">
                <span className="w-6 shrink-0 font-semibold text-primary">{String(index + 1).padStart(2, "0")}</span>
                {rule}
              </li>
            ))}
          </ol>
        </section>

        <section className="rounded-3xl bg-[#eff4ff] p-6">
          <h2 className="m-0 text-lg font-semibold text-ink">🛡️ Como a SelenIA age em situações de risco</h2>
          <p className="mt-1 text-sm text-muted">Protocolo de cuidado e encaminhamento</p>
          <ol className="mt-5 space-y-3 p-0">
            {guidelines.risk_behaviors.map((item, index) => (
              <li key={item} className="flex list-none gap-3 rounded-2xl bg-white p-4 text-sm leading-relaxed text-slate">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary-soft text-xs font-semibold text-primary">
                  {index + 1}
                </span>
                {item}
              </li>
            ))}
          </ol>
        </section>
      </div>

      <label className="mt-6 flex cursor-pointer flex-wrap items-center gap-3 rounded-2xl border border-line bg-white px-5 py-4">
        <input
          type="checkbox"
          checked={checked}
          disabled={alreadyAccepted}
          onChange={(e) => setChecked(e.target.checked)}
          className="h-5 w-5 accent-[#4a7c59]"
        />
        <span className="font-semibold text-ink">Li e entendi as regras da SelenIA</span>
        {alreadyAccepted && (
          <span className="ml-auto rounded-full bg-primary-soft px-3 py-1 text-sm text-primary">
            ✓ Aceito em {formatDateTime(professional.rules_accepted_at)}
          </span>
        )}
      </label>
      <div className="mt-4">
        <ErrorBox>{error}</ErrorBox>
      </div>

      <StepFooter step={4} onBack={() => goTo(3)}>
        <Button onClick={acceptRules} disabled={busy || !checked}>
          {busy ? "Salvando..." : "Continuar →"}
        </Button>
      </StepFooter>
    </div>
  );
}

// Etapa 5 — Suas regras extras (C5)
export function StepExtraRules({ professional, drafts, setDraft, save, goTo, busy, error }) {
  const [rules, updateRules] = useDraft(drafts, setDraft, "extra_never_say", professional.extra_never_say || []);
  const [newRule, setNewRule] = useDraft(drafts, setDraft, "new_rule", "");

  function addRule() {
    const text = newRule.trim();
    if (!text || rules.includes(text)) return;
    updateRules([...rules, text]);
    setNewRule("");
  }

  return (
    <div>
      <StepHeader eyebrow="PERSONALIZAÇÃO E LIMITES" title="Algo mais que a SelenIA nunca deve dizer?">
        Além das regras fixas, você pode acrescentar limites específicos do seu atendimento. Esta etapa é opcional.
      </StepHeader>

      <div className="mt-8 flex flex-col gap-3 sm:flex-row">
        <input
          className={`${inputClass} mt-0 flex-1`}
          value={newRule}
          onChange={(e) => setNewRule(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              addRule();
            }
          }}
          placeholder="Ex.: não comentar o trabalho de colegas"
          maxLength={300}
        />
        <Button variant="soft" onClick={addRule} disabled={!newRule.trim() || rules.length >= 30}>
          + Adicionar regra
        </Button>
      </div>

      <ul className="mt-6 space-y-3 p-0">
        {rules.map((rule) => (
          <li key={rule} className="flex list-none items-center gap-3 rounded-2xl bg-[#eff4ff] px-5 py-4 text-slate">
            <span className="text-primary">🛡️</span>
            <span className="flex-1">{rule}</span>
            <button
              type="button"
              onClick={() => updateRules(rules.filter((r) => r !== rule))}
              className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-xl border-0 bg-transparent text-muted transition-colors hover:bg-danger-soft hover:text-danger"
              aria-label={`Remover: ${rule}`}
              title="Remover regra"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M3 6h18" />
                <path d="M8 6V4h8v2" />
                <path d="M19 6l-1 14H6L5 6" />
                <path d="M10 11v6M14 11v6" />
              </svg>
            </button>
          </li>
        ))}
      </ul>

      <button
        type="button"
        onClick={() => goTo(4)}
        className="mt-6 cursor-pointer border-0 bg-transparent p-0 text-sm text-primary underline"
      >
        Rever as regras fixas
      </button>
      <div className="mt-4">
        <ErrorBox>{error}</ErrorBox>
      </div>

      <StepFooter step={5} onBack={() => goTo(4)}>
        <Button variant="ghost" onClick={() => save({}, 6)} disabled={busy}>
          Pular esta etapa
        </Button>
        <Button onClick={() => save({ extra_never_say: rules }, 6)} disabled={busy}>
          {busy ? "Salvando..." : "Continuar →"}
        </Button>
      </StepFooter>
    </div>
  );
}

// Etapa 6 — Conectar seu WhatsApp (C6). A conexão com a Meta (SMS,
// código e registro do número) entra em 05/10, no plano; até lá, esta
// etapa mostra o que vai ser pedido e segue por "Conectar depois".
export function StepWhatsApp({ professional, drafts, setDraft, save, goTo, busy, error }) {
  const [number, setNumber] = useDraft(drafts, setDraft, "whatsapp_number", "");
  const [displayName, setDisplayName] = useDraft(drafts, setDraft, "whatsapp_display_name", professional.name);

  return (
    <div>
      <StepHeader eyebrow="CANAL DE ATENDIMENTO" title="Conecte o número de atendimento">
        É neste número que a SelenIA vai receber e responder as mensagens das pessoas que procuram você, pela plataforma
        oficial do WhatsApp.
      </StepHeader>

      <div className="mt-6 flex gap-3 rounded-2xl border border-warning/30 bg-warning-soft px-5 py-4">
        <span aria-hidden="true">⚠️</span>
        <div className="text-sm leading-relaxed text-[#92400e]">
          <p className="m-0 font-semibold">Atenção antes de conectar</p>
          <p className="m-0 mt-1">
            O número conectado fica exclusivo da SelenIA e deixa de funcionar no aplicativo do WhatsApp e no WhatsApp
            Web. Você responde às pessoas pelo painel. Se quiser usar o número que já atende, apague a conta do
            WhatsApp dele no celular antes; as conversas antigas não são trazidas.
          </p>
        </div>
      </div>

      <div className="mt-8 space-y-6">
        <Field label="Número de WhatsApp" required>
          <div className="mt-2 flex overflow-hidden rounded-2xl border border-line bg-white focus-within:border-primary">
            {/* Bandeira desenhada: o Windows não mostra emoji de bandeira (aparece "BR"). */}
            <span className="flex shrink-0 items-center gap-2 whitespace-nowrap bg-[#eff4ff] px-4 text-slate">
              <svg width="22" height="16" viewBox="0 0 22 16" aria-hidden="true" className="rounded-sm">
                <rect width="22" height="16" fill="#009c3b" />
                <path d="M11 2 L20 8 L11 14 L2 8 Z" fill="#ffdf00" />
                <circle cx="11" cy="8" r="3.4" fill="#002776" />
              </svg>
              +55
            </span>
            <input
              className="w-full border-0 px-4 py-3 text-base outline-none"
              value={number}
              onChange={(e) => setNumber(e.target.value)}
              placeholder="(11) 98452-7810"
              inputMode="tel"
            />
          </div>
        </Field>
        <Field
          label="Nome que aparece no WhatsApp"
          required
          hint="Este nome passa por uma análise do WhatsApp antes de aparecer para as pessoas."
        >
          <input className={inputClass} value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
        </Field>

        <Button className="w-full" disabled title="Disponível em breve">
          Enviar código por SMS
        </Button>
        <p className="rounded-2xl bg-[#eff4ff] px-4 py-3 text-center text-sm text-slate">
          A conexão com o WhatsApp chega em breve. Por enquanto, clique em <strong>Conectar depois</strong>: dá para
          conectar mais tarde, pelo painel.
        </p>
        <ErrorBox>{error}</ErrorBox>
      </div>

      <StepFooter step={6} onBack={() => goTo(5)}>
        <Button onClick={() => save({}, 7)} disabled={busy}>
          Conectar depois →
        </Button>
      </StepFooter>
    </div>
  );
}

// Etapa 7 — Revisão (C9)
export function StepReview({ professional, guidelines, goTo, complete, busy, error, missing }) {
  const filledExamples = guidelines.voice_questions.filter(
    (q) => professional.voice_examples?.[q.key]?.good?.trim() && professional.voice_examples?.[q.key]?.bad?.trim()
  ).length;
  const extras = professional.extra_never_say || [];

  const blocks = [
    {
      step: 1,
      title: "SEUS DADOS",
      body: (
        <>
          <p className="m-0 font-semibold text-ink">{professional.name}</p>
          <p className="m-0 text-sm text-muted">
            {guidelines.pronoun_options.find((o) => o.key === professional.pronouns)?.label || "Pronomes não escolhidos"}
          </p>
          <p className="m-0 text-sm text-muted">{professional.alert_email}</p>
        </>
      ),
    },
    {
      step: 2,
      title: "ATENDIMENTO",
      body: (
        <p className="m-0 line-clamp-3 text-slate">
          {professional.audience_description} • Sessões de {professional.session_minutes} minutos •{" "}
          {professional.service_info}
        </p>
      ),
    },
    {
      step: 3,
      title: "TOM DE VOZ",
      body: (
        <>
          <p className="m-0 text-slate">{professional.voice_tone}</p>
          <span className="mt-2 inline-block rounded-full bg-[#eff4ff] px-3 py-1 text-xs text-slate">
            {filledExamples} de {guidelines.voice_questions.length} exemplos preenchidos
          </span>
        </>
      ),
    },
    {
      step: 4,
      title: "REGRAS DA SELENIA",
      body: professional.rules_accepted_at ? (
        <span className="inline-block rounded-full bg-primary-soft px-3 py-1 text-sm text-primary">
          ✓ Lidas e aceitas em {formatDateTime(professional.rules_accepted_at)}
        </span>
      ) : (
        <span className="text-sm text-danger">Ainda não aceitas</span>
      ),
    },
    {
      step: 5,
      title: "REGRAS EXTRAS",
      body: extras.length ? (
        <ul className="m-0 space-y-1 pl-5 text-slate">
          {extras.map((rule) => (
            <li key={rule}>{rule}</li>
          ))}
        </ul>
      ) : (
        <p className="m-0 text-sm text-muted">Nenhuma regra extra</p>
      ),
    },
    {
      step: 6,
      title: "WHATSAPP",
      body: (
        <span className="inline-block rounded-full bg-warning-soft px-3 py-1 text-sm text-[#92400e]">
          Não conectado – você pode conectar depois
        </span>
      ),
    },
  ];

  return (
    <div>
      <StepHeader eyebrow="ETAPA FINAL" title="Tudo certo? Revise antes de concluir">
        Você pode mudar qualquer informação depois, em Perfil do atendimento.
      </StepHeader>

      <div className="mt-8 space-y-4">
        {blocks.map((block) => (
          <div key={block.step} className="flex items-start gap-4 rounded-2xl bg-[#eff4ff] p-5">
            <div className="flex-1">
              <p className="m-0 mb-1 text-xs font-semibold tracking-wider text-muted">{block.title}</p>
              {block.body}
            </div>
            <Button variant="ghost" className="bg-white px-4 py-2 text-sm text-primary" onClick={() => goTo(block.step)}>
              ✎ Editar
            </Button>
          </div>
        ))}
      </div>

      {missing?.length > 0 && (
        <div className="mt-6 rounded-2xl bg-danger-soft px-5 py-4 text-sm text-danger" role="alert">
          <p className="m-0 font-semibold">Falta preencher:</p>
          <ul className="m-0 mt-2 pl-5">
            {missing.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="mt-4">
        <ErrorBox>{!missing?.length && error}</ErrorBox>
      </div>

      <div className="mt-8 text-center">
        <Button onClick={complete} disabled={busy} className="px-10">
          {busy ? "Concluindo..." : "Concluir cadastro →"}
        </Button>
        <p className="mt-3 text-sm text-muted">Ao concluir, a SelenIA começa a atender com estas configurações.</p>
      </div>
      <StepFooter step={7} onBack={() => goTo(6)} />
    </div>
  );
}

// Cadastro concluído (C10)
export function Done({ professional, onFinished }) {
  return (
    <div className="py-6 text-center">
      <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-primary-soft text-4xl text-primary">
        ✓
      </div>
      <p className="mt-6 inline-block rounded-full bg-primary-soft px-4 py-1 text-xs font-semibold tracking-wider text-primary">
        CONFIGURAÇÃO FINALIZADA
      </p>
      <h1 className="mt-4 text-4xl font-bold tracking-tight text-ink">Tudo pronto, {professional.name}!</h1>
      <p className="mx-auto mt-4 max-w-md text-lg text-muted">
        A <strong className="text-primary">SelenIA</strong> já está configurada. Antes de liberar para as pessoas, que
        tal testar como ela responde?
      </p>
      <div className="mx-auto mt-8 flex max-w-lg flex-col gap-3 sm:flex-row">
        <Button variant="soft" className="flex-1" onClick={() => onFinished("testar")}>
          💬 Testar a SelenIA
        </Button>
        <Button className="flex-1" onClick={() => onFinished()}>
          Ir para o painel →
        </Button>
      </div>
    </div>
  );
}
