import { useEffect, useRef, useState } from "react";

import { api } from "../api.js";
import { usePanel } from "./PanelContext.jsx";

const DURATIONS = [
  { minutes: 50, label: "50 minutos" },
  { minutes: 90, label: "1h30" },
  { minutes: null, label: "Até eu desligar" },
];

function formatTime(iso) {
  return new Date(iso).toLocaleTimeString("pt-BR", {
    timeZone: "America/Sao_Paulo",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// Botão "Em consulta" da barra do topo (protótipo: Conversas). Enquanto
// ligado, quem pedir para falar com a profissional recebe um aviso fixo
// e a MarIA segue ajudando. Ver funcionalidades/handoff-e-em-consulta.md.
export default function InSessionControl() {
  const { professional, setProfessional } = usePanel();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const menuRef = useRef(null);

  useEffect(() => {
    function close(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) setOpen(false);
    }
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  async function act(action) {
    setBusy(true);
    setError("");
    try {
      setProfessional(await action());
      setOpen(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const start = (minutes) => act(() => api.startSession(professional.slug, minutes));
  const end = () => act(() => api.endSession(professional.slug));
  // "+15 min": recomeça contando o que falta mais 15 (teto de 4 horas).
  const extend = () => {
    const left = Math.ceil((new Date(professional.in_session_until) - Date.now()) / 60000);
    return start(Math.min(240, Math.max(0, left) + 15));
  };

  if (professional.in_session) {
    return (
      <div className="flex items-center gap-2">
        <span className="rounded-full bg-primary px-3 py-1.5 text-xs font-semibold tracking-wide text-white">
          EM CONSULTA {professional.in_session_until ? `ATÉ ${formatTime(professional.in_session_until)}` : ""}
        </span>
        {professional.in_session_until && (
          <button
            type="button"
            onClick={extend}
            disabled={busy}
            className="cursor-pointer rounded-xl border-0 bg-[#eff4ff] px-3 py-1.5 text-sm text-slate hover:bg-[#dce9ff]"
          >
            +15 min
          </button>
        )}
        <button
          type="button"
          onClick={end}
          disabled={busy}
          className="cursor-pointer rounded-xl border-0 bg-danger-soft px-3 py-1.5 text-sm font-semibold text-danger hover:bg-[#fde2e2]"
        >
          Encerrar
        </button>
        {error && <span className="text-xs text-danger">{error}</span>}
      </div>
    );
  }

  return (
    <div className="relative" ref={menuRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="cursor-pointer rounded-xl border border-line bg-white px-4 py-2 text-sm font-semibold text-primary hover:bg-primary-soft"
      >
        Entrar em consulta ▾
      </button>
      {open && (
        <div className="absolute right-0 z-30 mt-2 w-72 rounded-2xl border border-line bg-white p-3 shadow-lg">
          <p className="m-0 px-2 text-xs font-semibold tracking-wider text-muted">DURAÇÃO</p>
          {DURATIONS.map((d) => (
            <button
              key={d.label}
              type="button"
              disabled={busy}
              onClick={() => start(d.minutes)}
              className="mt-1 block w-full cursor-pointer rounded-xl border-0 bg-transparent px-2 py-2 text-left text-sm text-ink hover:bg-primary-soft"
            >
              {d.label}
            </button>
          ))}
          <p className="m-0 mt-2 border-t border-line px-2 pt-2 text-xs leading-relaxed text-muted">
            Quem pedir para falar com você recebe um aviso de que você está em atendimento, e a MarIA segue ajudando.
            Emergências continuam gerando alerta na hora.
          </p>
          {error && <p className="m-0 mt-2 px-2 text-xs text-danger">{error}</p>}
        </div>
      )}
    </div>
  );
}
