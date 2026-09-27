import { useEffect, useState } from "react";

import { api } from "../api.js";
import Logo from "../components/Logo.jsx";
import {
  Done,
  STEPS,
  StepData,
  StepExtraRules,
  StepReview,
  StepRules,
  StepService,
  StepVoice,
  StepWhatsApp,
} from "./onboarding/Steps.jsx";

// Cadastro em 7 etapas (protótipo: C1 a C10). Cada "Continuar" grava no
// backend, inclusive a etapa em que ela está: fechando o navegador no
// meio, volta de onde parou. O painel só libera com o cadastro concluído.
export default function Onboarding({ me, onFinished, onLogout }) {
  const [professional, setProfessional] = useState(me.professional);
  const [guidelines, setGuidelines] = useState(null);
  const [step, setStep] = useState(me.professional ? Math.max(2, me.professional.onboarding_step || 2) : 1);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [missing, setMissing] = useState([]);
  // O que foi digitado e ainda não passou pelo "Continuar", de todas as
  // etapas: sobrevive à ida e volta entre elas. Some se a página for
  // recarregada; o que vale é o que foi gravado.
  const [drafts, setDrafts] = useState({});
  const setDraft = (key, value) => setDrafts((prev) => ({ ...prev, [key]: value }));

  useEffect(() => {
    api
      .getGuidelines()
      .then(setGuidelines)
      .catch((err) => setError(err.message));
  }, []);

  // Etapa mais adiantada já alcançada: até ela, a barra de progresso deixa voltar.
  const reached = professional ? Math.max(professional.onboarding_step || 2, step) : 1;

  function goTo(target) {
    setError("");
    setMissing([]);
    setStep(target);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function run(action) {
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  // Grava os campos da etapa e avança. A etapa salva nunca volta para trás
  // quando ela edita algo pela revisão.
  function save(fields, nextStep) {
    return run(async () => {
      let current = professional;
      if (!current) {
        try {
          setProfessional(await api.createProfessional(fields));
          goTo(nextStep);
          return;
        } catch (err) {
          // A conta já tem cadastro, mas esta tela não sabia (outra aba,
          // ou a página ficou com dados velhos): busca o cadastro e segue
          // gravando nele, em vez de travar na etapa 1.
          if (err.status !== 409) throw err;
          current = (await api.me()).professional;
          if (!current) throw err;
        }
      }
      const onboarding_step = Math.max(current.onboarding_step || 2, nextStep);
      setProfessional(await api.updateProfessional(current.slug, { ...fields, onboarding_step }));
      goTo(nextStep);
    });
  }

  function acceptRules() {
    return run(async () => {
      if (!professional.rules_accepted_at) await api.acceptRules(professional.slug);
      const updated = await api.updateProfessional(professional.slug, {
        onboarding_step: Math.max(professional.onboarding_step || 2, 5),
      });
      setProfessional(updated);
      goTo(5);
    });
  }

  function complete() {
    setMissing([]);
    return run(async () => {
      try {
        setProfessional(await api.completeOnboarding(professional.slug));
        setDone(true);
        window.scrollTo({ top: 0 });
      } catch (err) {
        if (err.detail?.missing) setMissing(err.detail.missing);
        throw err;
      }
    });
  }

  const stepProps = { professional, me, guidelines, drafts, setDraft, save, goTo, busy, error };

  return (
    <div className="min-h-screen px-4 py-8 sm:py-10">
      <header className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4">
        <Logo />
        <div className="flex items-center gap-3 rounded-full border border-line bg-white py-1.5 pl-1.5 pr-4 text-sm">
          {me.picture_url && (
            <img src={me.picture_url} alt="" className="h-8 w-8 rounded-full" referrerPolicy="no-referrer" />
          )}
          <span className="hidden text-slate sm:inline">{me.email}</span>
          <button
            type="button"
            onClick={onLogout}
            className="cursor-pointer border-0 bg-transparent p-0 text-muted hover:text-ink"
          >
            Sair
          </button>
        </div>
      </header>

      {!done && (
        <nav
          aria-label="Etapas do cadastro"
          className="mx-auto mt-8 max-w-5xl overflow-x-auto rounded-3xl border border-line bg-white px-4 py-4"
        >
          <ol className="m-0 flex min-w-max justify-between gap-2 p-0">
            {STEPS.map((label, index) => {
              const number = index + 1;
              const current = number === step;
              const finished = number < reached && !current;
              const clickable = professional && number <= reached && !current;
              return (
                <li key={label} className="list-none">
                  <button
                    type="button"
                    disabled={!clickable}
                    onClick={() => goTo(number)}
                    className="flex cursor-pointer flex-col items-center gap-1 border-0 bg-transparent px-2 disabled:cursor-default"
                  >
                    <span
                      className={`flex h-9 w-9 items-center justify-center rounded-full text-sm font-semibold ${
                        current
                          ? "bg-primary text-white ring-4 ring-primary/20"
                          : finished
                            ? "bg-primary-dark text-white"
                            : "bg-[#eff4ff] text-muted"
                      }`}
                    >
                      {finished ? "✓" : number}
                    </span>
                    <span className={`text-xs ${current ? "font-semibold text-primary" : "text-muted"}`}>{label}</span>
                  </button>
                </li>
              );
            })}
          </ol>
        </nav>
      )}

      <main className="mx-auto mt-6 max-w-3xl rounded-3xl border border-line bg-white px-6 py-8 shadow-sm sm:px-10">
        {!guidelines ? (
          error ? (
            <p className="text-danger">{error}</p>
          ) : (
            <p className="text-muted">Carregando...</p>
          )
        ) : done ? (
          <Done professional={professional} onFinished={onFinished} />
        ) : step === 1 ? (
          <StepData {...stepProps} />
        ) : step === 2 ? (
          <StepService {...stepProps} />
        ) : step === 3 ? (
          <StepVoice {...stepProps} />
        ) : step === 4 ? (
          <StepRules {...stepProps} acceptRules={acceptRules} />
        ) : step === 5 ? (
          <StepExtraRules {...stepProps} />
        ) : step === 6 ? (
          <StepWhatsApp {...stepProps} />
        ) : (
          <StepReview {...stepProps} complete={complete} missing={missing} />
        )}
      </main>
    </div>
  );
}
