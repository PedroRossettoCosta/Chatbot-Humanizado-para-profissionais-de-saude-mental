import { useEffect, useRef, useState } from "react";

import { api } from "../api.js";
import Logo from "../components/Logo.jsx";
import { loadGoogle } from "../google.js";


// Tela de login (protótipo: login_e_acesso_maria). Um botão só: quem
// entra pela primeira vez cai no cadastro; quem já tem conta, no painel.
export default function Login({ onLogin }) {
  const buttonRef = useRef(null);
  const [error, setError] = useState("");
  const [notInvited, setNotInvited] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function setup() {
      try {
        const { google_client_id: clientId } = await api.getAuthConfig();
        if (!clientId) {
          setError("O login com Google ainda não foi configurado (GOOGLE_CLIENT_ID).");
          return;
        }
        const google = await loadGoogle();
        if (cancelled) return;
        google.accounts.id.initialize({ client_id: clientId, callback: handleCredential });
        google.accounts.id.renderButton(buttonRef.current, {
          theme: "outline",
          size: "large",
          shape: "pill",
          text: "continue_with",
          locale: "pt-BR",
          width: 320,
        });
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }

    async function handleCredential({ credential }) {
      setBusy(true);
      setError("");
      setNotInvited(false);
      try {
        onLogin(await api.loginWithGoogle(credential));
      } catch (err) {
        if (err.status === 403) setNotInvited(true);
        else setError(err.message);
      } finally {
        setBusy(false);
      }
    }

    setup();
    return () => {
      cancelled = true;
    };
  }, [onLogin]);

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-12">
      <div className="w-full max-w-xl">
        <div className="overflow-hidden rounded-3xl border border-line bg-white shadow-sm">
          <div className="h-1.5 bg-gradient-to-r from-primary-soft via-primary to-primary-soft" />
          <div className="px-8 py-10 text-center sm:px-12">
            <Logo className="justify-center" />

            <h1 className="mt-8 text-3xl font-bold leading-tight tracking-tight text-ink">
              Sua assistente de atendimento, com segurança para você e seus pacientes
            </h1>
            <p className="mt-4 text-base leading-relaxed text-muted">
              Atendimento inicial humanizado, triagem de risco e alerta para você, pensados para a rotina de
              psicólogos, psicanalistas e terapeutas.
            </p>

            <div className="mt-8 flex min-h-11 justify-center" ref={buttonRef} aria-busy={busy} />
            <p className="mt-3 text-sm text-muted">Primeiro acesso? Entre com o Google e complete seu cadastro.</p>

            {busy && <p className="mt-4 text-sm text-muted">Entrando...</p>}

            {notInvited && (
              <div className="mt-6 rounded-2xl border border-warning/30 bg-warning-soft px-5 py-4 text-left">
                <p className="font-semibold text-slate">Acesso ainda não liberado</p>
                <p className="mt-1 text-sm text-muted">
                  Seu e-mail ainda não tem convite para a fase de testes. Se você usou a conta errada, clique no botão
                  acima e escolha outra.
                </p>
              </div>
            )}

            {error && (
              <p className="mt-6 rounded-2xl bg-danger-soft px-5 py-3 text-sm text-danger" role="alert">
                {error}
              </p>
            )}

            <div className="mt-8 flex items-start gap-3 rounded-2xl bg-primary-soft px-5 py-4 text-left">
              <span className="mt-0.5 text-primary" aria-hidden="true">
                ✓
              </span>
              <div>
                <p className="font-semibold text-slate">Acesso por convite</p>
                <p className="text-sm text-muted">A SelenIA está em fase de testes, e por enquanto o acesso é só por convite.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
