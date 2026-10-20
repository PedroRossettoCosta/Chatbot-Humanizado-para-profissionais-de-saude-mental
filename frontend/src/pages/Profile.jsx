import { useEffect, useMemo, useState } from "react";

import { api } from "../api.js";
import { LockIcon, TrashIcon } from "../components/icons.jsx";
import MultiSelect from "../components/MultiSelect.jsx";
import { Button, ErrorBox, Field, formatDateTime, inputClass } from "../components/ui.jsx";
import { usePanel } from "../panel/PanelContext.jsx";

const SECTIONS = [
  { id: "dados", label: "Seus dados" },
  { id: "atendimento", label: "Atendimento" },
  { id: "tom", label: "Tom de voz" },
  { id: "extras", label: "Regras extras" },
  { id: "regras", label: "Regras da SelenIA" },
];

function formFrom(p) {
  return {
    name: p.name || "",
    pronouns: p.pronouns || "",
    alert_email: p.alert_email || "",
    audience_description: p.audience_description || "",
    service_info: p.service_info || "",
    session_minutes: p.session_minutes ? String(p.session_minutes) : "",
    payment_methods: p.payment_methods || [],
    voice_tone: p.voice_tone || "",
    voice_examples: p.voice_examples || {},
    extra_never_say: p.extra_never_say || [],
  };
}

function Card({ id, eyebrow, title, children }) {
  return (
    <section id={id} className="scroll-mt-24 rounded-3xl border border-line bg-white p-6 shadow-sm sm:p-8">
      <p className="m-0 text-xs font-semibold tracking-wider text-primary">{eyebrow}</p>
      <h2 className="m-0 mt-1 text-2xl font-semibold tracking-tight text-ink">{title}</h2>
      <div className="mt-6 space-y-6">{children}</div>
    </section>
  );
}

// Perfil do atendimento (protótipo: perfil_do_atendimento_maria). Os
// mesmos campos do cadastro numa página só; nada é gravado até "Salvar
// alterações".
export default function Profile() {
  const { professional, setProfessional, openSimulator } = usePanel();
  const [guidelines, setGuidelines] = useState(null);
  const [form, setForm] = useState(() => formFrom(professional));
  const [newRule, setNewRule] = useState("");
  const [showRules, setShowRules] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api
      .getGuidelines()
      .then(setGuidelines)
      .catch((err) => setError(err.message));
  }, []);

  const original = useMemo(() => formFrom(professional), [professional]);
  const dirty = JSON.stringify(form) !== JSON.stringify(original);

  const set = (field) => (value) => {
    setSaved(false);
    setForm((prev) => ({ ...prev, [field]: value }));
  };
  const setExample = (key, which, value) =>
    set("voice_examples")({ ...form.voice_examples, [key]: { ...form.voice_examples[key], [which]: value } });

  function addRule() {
    const text = newRule.trim();
    if (!text || form.extra_never_say.includes(text)) return;
    set("extra_never_say")([...form.extra_never_say, text]);
    setNewRule("");
  }

  const minutes = Number(form.session_minutes);
  const valid =
    form.name.trim() &&
    form.pronouns &&
    form.alert_email.trim() &&
    form.audience_description.trim() &&
    form.service_info.trim() &&
    Number.isInteger(minutes) &&
    minutes >= 15 &&
    minutes <= 240 &&
    form.voice_tone.trim();

  async function saveChanges() {
    setSaving(true);
    setError("");
    try {
      const updated = await api.updateProfessional(professional.slug, {
        ...form,
        name: form.name.trim(),
        alert_email: form.alert_email.trim(),
        session_minutes: minutes,
      });
      setProfessional(updated);
      setForm(formFrom(updated));
      setSaved(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (!guidelines) return <p className="text-muted">{error || "Carregando..."}</p>;

  return (
    <div className="mx-auto max-w-6xl pb-28">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="m-0 text-xs font-semibold tracking-wider text-primary">CONFIGURAÇÕES DO ATENDIMENTO</p>
          <h1 className="m-0 mt-2 text-4xl font-bold tracking-tight text-ink">Perfil do atendimento</h1>
          <p className="m-0 mt-2 max-w-2xl text-muted">
            Como a SelenIA apresenta você, o tom de voz dela e os limites do seu atendimento.
          </p>
        </div>
        <Button variant="soft" onClick={openSimulator}>
          Testar a SelenIA
        </Button>
      </div>

      <div className="mt-8 grid gap-8 lg:grid-cols-[200px_1fr]">
        <nav className="hidden lg:block">
          <div className="sticky top-24 rounded-3xl border border-line bg-white p-4">
            <p className="m-0 mb-2 text-xs font-semibold tracking-wider text-muted">NESTA PÁGINA</p>
            {SECTIONS.map((s) => (
              <a key={s.id} href={`#${s.id}`} className="block rounded-xl px-3 py-2 text-sm text-slate no-underline hover:bg-primary-soft">
                {s.label}
              </a>
            ))}
          </div>
        </nav>

        <div className="min-w-0 space-y-6">
          <Card id="dados" eyebrow="ETAPA 1" title="Seus dados">
            <div className="grid gap-6 md:grid-cols-2 [&>*]:min-w-0">
              <Field label="Nome de exibição" required hint="É como a SelenIA vai se referir a você nas conversas.">
                <input className={inputClass} value={form.name} onChange={(e) => set("name")(e.target.value)} />
              </Field>
              <Field label="Como a SelenIA deve falar de você" required>
                <select
                  className={`${inputClass} cursor-pointer`}
                  value={form.pronouns}
                  onChange={(e) => set("pronouns")(e.target.value)}
                >
                  <option value="" disabled>
                    Escolha uma opção
                  </option>
                  {guidelines.pronoun_options.map((o) => (
                    <option key={o.key} value={o.key}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </Field>
            </div>
            <Field label="E-mail para alertas" required hint="🔒 O e-mail não inclui o conteúdo da conversa.">
              <input
                className={inputClass}
                type="email"
                value={form.alert_email}
                onChange={(e) => set("alert_email")(e.target.value)}
              />
            </Field>
          </Card>

          <Card id="atendimento" eyebrow="ETAPA 2" title="Atendimento">
            <Field label="Especialidade e público" required>
              <textarea
                className={`${inputClass} min-h-24`}
                value={form.audience_description}
                onChange={(e) => set("audience_description")(e.target.value)}
              />
            </Field>
            <Field label="Informações do serviço" required hint="A SelenIA informa o valor já na primeira pergunta sobre preço.">
              <textarea
                className={`${inputClass} min-h-24`}
                value={form.service_info}
                onChange={(e) => set("service_info")(e.target.value)}
              />
            </Field>
            {/* Fora do <Field>: o rótulo envolveria a lista e um clique numa
                opção abriria e fecharia o botão. */}
            <div>
              <span className="font-semibold text-slate">Formas de pagamento aceitas</span>
              <MultiSelect
                ariaLabel="Formas de pagamento aceitas"
                options={guidelines.payment_options}
                value={form.payment_methods}
                onChange={set("payment_methods")}
                placeholder="Escolha uma ou mais formas"
              />
              <span className="mt-2 block text-sm text-muted">
                A SelenIA só informa as formas marcadas. Sem nenhuma marcada, ela pergunta a você por e-mail quando
                alguém quiser saber como pagar.
              </span>
            </div>
            <Field label="Duração da sessão (minutos)" required hint="Usada pela agenda para oferecer horários.">
              <input
                className={`${inputClass} max-w-32`}
                type="number"
                min={15}
                max={240}
                value={form.session_minutes}
                onChange={(e) => set("session_minutes")(e.target.value)}
              />
            </Field>
          </Card>

          <Card id="tom" eyebrow="ETAPA 3" title="Tom de voz">
            <Field label="Tom de voz" required>
              <input className={inputClass} value={form.voice_tone} onChange={(e) => set("voice_tone")(e.target.value)} />
            </Field>
            {guidelines.voice_questions.map((q) => (
              <div key={q.key} className="rounded-3xl bg-[#eff4ff] p-5">
                <p className="m-0 font-semibold text-ink">“{q.question}”</p>
                <div className="mt-4 grid gap-4 md:grid-cols-2 [&>*]:min-w-0">
                  <Field label="✓ Resposta boa">
                    <textarea
                      className={`${inputClass} min-h-24`}
                      value={form.voice_examples[q.key]?.good || ""}
                      onChange={(e) => setExample(q.key, "good", e.target.value)}
                    />
                  </Field>
                  <Field label="✕ Resposta ruim">
                    <textarea
                      className={`${inputClass} min-h-24`}
                      value={form.voice_examples[q.key]?.bad || ""}
                      onChange={(e) => setExample(q.key, "bad", e.target.value)}
                    />
                  </Field>
                </div>
              </div>
            ))}
          </Card>

          <Card id="extras" eyebrow="ETAPA 5" title="Regras extras">
            <div className="flex flex-col gap-3 sm:flex-row">
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
              <Button variant="soft" onClick={addRule} disabled={!newRule.trim() || form.extra_never_say.length >= 30}>
                + Adicionar regra
              </Button>
            </div>
            <ul className="m-0 space-y-3 p-0">
              {form.extra_never_say.length === 0 && <li className="list-none text-sm text-muted">Nenhuma regra extra.</li>}
              {form.extra_never_say.map((rule) => (
                <li key={rule} className="flex list-none items-center gap-3 rounded-2xl bg-[#eff4ff] px-5 py-3 text-slate">
                  <span className="flex-1">{rule}</span>
                  <button
                    type="button"
                    onClick={() => set("extra_never_say")(form.extra_never_say.filter((r) => r !== rule))}
                    className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-xl border-0 bg-transparent text-muted transition-colors hover:bg-danger-soft hover:text-danger"
                    aria-label={`Remover: ${rule}`}
                    title="Remover regra"
                  >
                    <TrashIcon size={18} />
                  </button>
                </li>
              ))}
            </ul>
          </Card>

          <section id="regras" className="scroll-mt-24 rounded-3xl border border-line bg-white p-6 shadow-sm sm:p-8">
            <div className="flex flex-wrap items-center gap-4">
              <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary-soft text-primary">
                <LockIcon />
              </span>
              <div className="flex-1">
                <h2 className="m-0 text-xl font-semibold text-ink">Regras da SelenIA</h2>
                <p className="m-0 text-sm text-muted">Iguais em todas as contas; não podem ser alteradas.</p>
              </div>
              {professional.rules_accepted_at && (
                <span className="rounded-full bg-primary-soft px-3 py-1 text-sm text-primary">
                  ✓ Lidas e aceitas em {formatDateTime(professional.rules_accepted_at)}
                </span>
              )}
              <button
                type="button"
                onClick={() => setShowRules((v) => !v)}
                className="cursor-pointer border-0 bg-transparent p-0 text-sm font-semibold text-primary hover:underline"
              >
                {showRules ? "Esconder regras" : "Ver regras"}
              </button>
            </div>
            {showRules && (
              <div className="mt-6 grid gap-6 lg:grid-cols-2">
                <div>
                  <p className="m-0 mb-3 font-semibold text-ink">A SelenIA nunca diz</p>
                  <ol className="m-0 space-y-2 pl-5 text-sm leading-relaxed text-slate">
                    {guidelines.never_say.map((r) => (
                      <li key={r}>{r}</li>
                    ))}
                  </ol>
                </div>
                <div>
                  <p className="m-0 mb-3 font-semibold text-ink">Como a SelenIA age em situações de risco</p>
                  <ol className="m-0 space-y-2 pl-5 text-sm leading-relaxed text-slate">
                    {guidelines.risk_behaviors.map((r) => (
                      <li key={r}>{r}</li>
                    ))}
                  </ol>
                </div>
              </div>
            )}
          </section>
        </div>
      </div>

      {(dirty || saved || error) && (
        <div className="fixed inset-x-0 bottom-4 z-30 flex justify-center px-4">
          <div className="flex w-full max-w-3xl flex-wrap items-center gap-3 rounded-2xl bg-ink px-5 py-3 text-white shadow-2xl">
            {error ? (
              <div className="flex-1">
                <ErrorBox>{error}</ErrorBox>
              </div>
            ) : dirty ? (
              <div className="flex-1">
                <p className="m-0 font-semibold">Você tem alterações não salvas</p>
                {!valid && <p className="m-0 text-sm text-white/70">Preencha os campos obrigatórios para salvar.</p>}
              </div>
            ) : (
              <p className="m-0 flex-1 font-semibold">✓ Alterações salvas</p>
            )}
            {dirty && (
              <>
                <Button
                  variant="ghost"
                  className="text-white hover:bg-white/10"
                  onClick={() => {
                    setForm(original);
                    setError("");
                  }}
                >
                  Descartar
                </Button>
                <Button onClick={saveChanges} disabled={saving || !valid}>
                  {saving ? "Salvando..." : "Salvar alterações"}
                </Button>
              </>
            )}
            {!dirty && (
              <Button variant="ghost" className="text-white hover:bg-white/10" onClick={() => { setSaved(false); setError(""); }}>
                Fechar
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
