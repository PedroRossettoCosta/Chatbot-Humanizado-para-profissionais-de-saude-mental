import { useState } from "react";

import { api } from "../api.js";
import Logo from "../components/Logo.jsx";

// Primeira etapa do cadastro (protótipo: c1_etapa_1_de_7_seus_dados).
// As outras etapas entram com o cadastro completo; por enquanto, depois
// desta o resto do perfil é preenchido no painel.
export default function SignupStart({ me, onCreated, onLogout }) {
  const [name, setName] = useState(me.name || "");
  const [alertEmail, setAlertEmail] = useState(me.email);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      await api.createProfessional({ name: name.trim(), alert_email: alertEmail.trim() });
      onCreated();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  const inputClass =
    "mt-2 w-full rounded-2xl border border-line bg-white px-4 py-3 text-base text-ink outline-none focus:border-primary focus:ring-4 focus:ring-primary/15";

  return (
    <div className="min-h-screen px-4 py-10">
      <header className="mx-auto flex max-w-4xl items-center justify-between gap-4">
        <Logo />
        <div className="flex items-center gap-3 rounded-full border border-line bg-white py-1.5 pl-1.5 pr-4 text-sm">
          {me.picture_url && <img src={me.picture_url} alt="" className="h-8 w-8 rounded-full" referrerPolicy="no-referrer" />}
          <span className="hidden text-slate sm:inline">{me.email}</span>
          <button type="button" onClick={onLogout} className="cursor-pointer border-0 bg-transparent p-0 text-muted hover:text-ink">
            Sair
          </button>
        </div>
      </header>

      <main className="mx-auto mt-10 max-w-2xl rounded-3xl border border-line bg-white px-6 py-8 shadow-sm sm:px-10">
        <p className="text-xs font-semibold tracking-wider text-primary">ETAPA INICIAL</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight">Vamos começar pelo básico</h1>
        <p className="mt-3 text-muted">
          Estas informações identificam você para as pessoas que procuram atendimento e definem para onde enviamos os
          avisos importantes.
        </p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-6">
          <label className="block">
            <span className="font-semibold text-slate">
              Nome de exibição <span className="text-danger">*</span>
            </span>
            <input className={inputClass} value={name} onChange={(e) => setName(e.target.value)} required maxLength={255} />
            <span className="mt-2 block text-sm text-muted">É como a MarIA vai se referir a você nas conversas.</span>
          </label>

          <label className="block">
            <span className="font-semibold text-slate">
              E-mail para alertas <span className="text-danger">*</span>
            </span>
            <input
              className={inputClass}
              type="email"
              value={alertEmail}
              onChange={(e) => setAlertEmail(e.target.value)}
              required
            />
            <span className="mt-2 block text-sm text-muted">
              Para onde enviamos os avisos de emergência. Por segurança, o e-mail não inclui o conteúdo da conversa.
            </span>
          </label>

          {error && (
            <p className="rounded-2xl bg-danger-soft px-4 py-3 text-sm text-danger" role="alert">
              {error}
            </p>
          )}

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={saving || !name.trim()}
              className="cursor-pointer rounded-2xl border-0 bg-primary px-6 py-3 text-base font-semibold text-white hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saving ? "Salvando..." : "Continuar"}
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}
