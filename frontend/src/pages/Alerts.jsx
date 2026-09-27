import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api } from "../api.js";
import { AlertIcon, ArrowLeftIcon, BellIcon, ChatIcon, LockIcon } from "../components/icons.jsx";
import { Button, ErrorBox, Tag, formatDateTime, formatTime, inputClass, shortWhen } from "../components/ui.jsx";
import { usePanel } from "../panel/PanelContext.jsx";

const REFRESH_MS = 10000;

const LEVELS = {
  emergency: { label: "Emergência", tone: "danger" },
  possible_risk: { label: "Dúvida sobre segurança", tone: "warning" },
  bot_refused: { label: "Recusou falar com a MarIA", tone: "info" },
};

const FILTERS = [
  { key: "all", label: "Todos", test: () => true },
  { key: "new", label: "Não revisados", test: (a) => a.status === "new" },
  { key: "emergency", label: "Emergência", test: (a) => a.level === "emergency" },
  { key: "possible_risk", label: "Dúvida sobre segurança", test: (a) => a.level === "possible_risk" },
  { key: "bot_refused", label: "Recusou a MarIA", test: (a) => a.level === "bot_refused" },
];

// Cor da bolinha de cada linha da trilha.
const DOTS = {
  created: "bg-danger",
  action: "bg-primary",
  notified: "bg-primary",
  notify_failed: "bg-danger",
  viewed: "bg-slate",
  reviewed: "bg-primary",
  bot_released: "bg-[#1e40af]",
};

function LevelTag({ level }) {
  const info = LEVELS[level] || { label: level, tone: "neutral" };
  return <Tag tone={info.tone}>{info.label}</Tag>;
}

function StatusTag({ alert }) {
  return alert.status === "new" ? <Tag tone="danger">Novo</Tag> : <Tag>Revisado</Tag>;
}

// Alertas e auditoria (protótipo: alertas_e_auditoria_maria; no celular,
// M4 e M5). Nada aqui edita ou apaga um alerta: abrir, revisar e liberar
// a MarIA entram na trilha.
export default function Alerts() {
  const { professional } = usePanel();
  const { alertId } = useParams();
  const [list, setList] = useState(null);
  const [filter, setFilter] = useState("all");
  const [error, setError] = useState("");

  const loadList = useCallback(() => {
    api
      .listAlerts(professional.slug)
      .then((data) => {
        setList(data);
        setError("");
      })
      .catch((err) => setError(err.message));
  }, [professional.slug]);

  useEffect(() => {
    loadList();
    const id = setInterval(loadList, REFRESH_MS);
    return () => clearInterval(id);
  }, [loadList]);

  const visible = useMemo(() => (list || []).filter(FILTERS.find((f) => f.key === filter).test), [list, filter]);
  const unreviewed = (list || []).filter((a) => a.status === "new").length;

  return (
    <div className="mx-auto grid h-[calc(100dvh-8.5rem)] min-h-[480px] max-w-7xl gap-6 lg:grid-cols-[440px_1fr] [&>*]:min-w-0">
      {/* Lista */}
      <section className={`min-h-0 flex-col ${alertId ? "hidden lg:flex" : "flex"}`}>
        <div className="rounded-3xl border border-line bg-white p-4">
          <div className="flex items-baseline justify-between gap-3">
            <h1 className="m-0 text-xl font-bold text-ink">Alertas</h1>
            <span className={`text-sm font-semibold ${unreviewed ? "text-danger" : "text-muted"}`}>
              {list ? `${unreviewed} sem revisar` : ""}
            </span>
          </div>
          <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
            {FILTERS.map((f) => {
              const count = (list || []).filter(f.test).length;
              return (
                <button
                  key={f.key}
                  type="button"
                  onClick={() => setFilter(f.key)}
                  className={`shrink-0 cursor-pointer whitespace-nowrap rounded-full border-0 px-3 py-1.5 text-sm font-medium ${
                    filter === f.key ? "bg-primary text-white" : "bg-[#eff4ff] text-slate hover:bg-primary-soft"
                  }`}
                >
                  {f.label} ({count})
                </button>
              );
            })}
          </div>
        </div>

        <div className="mt-2">
          <ErrorBox>{error}</ErrorBox>
        </div>

        <ul className="m-0 mt-2 min-h-0 flex-1 space-y-3 overflow-y-auto p-0 pb-2">
          {list === null && !error && <li className="list-none px-2 text-sm text-muted">Carregando...</li>}
          {list?.length === 0 && (
            <li className="list-none rounded-3xl bg-[#eff4ff] px-6 py-10 text-center">
              <span className="text-primary">
                <BellIcon size={28} />
              </span>
              <p className="m-0 mt-3 font-semibold text-ink">Nenhum alerta</p>
              <p className="m-0 mt-1 text-sm text-muted">
                Quando a triagem encontrar risco, ou alguém recusar falar com a MarIA, o alerta aparece aqui e um e-mail
                vai para você.
              </p>
            </li>
          )}
          {list?.length > 0 && visible.length === 0 && (
            <li className="list-none px-2 py-6 text-center text-sm text-muted">Nenhum alerta neste filtro.</li>
          )}
          {visible.map((a) => (
            <li key={a.id} className="list-none">
              <Link
                to={`/alertas/${a.id}`}
                className={`block rounded-3xl border-2 p-4 no-underline transition-colors ${
                  a.id === alertId ? "border-primary" : "border-transparent hover:border-line"
                } ${a.status === "new" && a.level === "emergency" ? "bg-[#fff7f7]" : "bg-white"}`}
              >
                <div className="flex flex-wrap items-center gap-1.5">
                  <LevelTag level={a.level} />
                  <StatusTag alert={a} />
                  {a.channel === "simulator" && <Tag>Teste</Tag>}
                  <span className="ml-auto text-xs text-muted">{shortWhen(a.created_at)}</span>
                </div>
                {a.excerpt && (
                  <p className="m-0 mt-3 line-clamp-3 rounded-2xl bg-canvas px-3 py-2 text-sm italic leading-snug text-slate">
                    "{a.excerpt}"
                  </p>
                )}
                <p className="m-0 mt-2 truncate text-sm text-muted">
                  {a.contact_name}
                  {a.contact_phone && a.contact_phone !== a.contact_name ? ` · ${a.contact_phone}` : ""}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      {/* Alerta aberto */}
      <section className={`min-h-0 ${alertId ? "flex" : "hidden lg:flex"}`}>
        {alertId ? (
          <AlertView key={alertId} alertId={alertId} onChanged={loadList} />
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center rounded-3xl border border-line bg-white p-8 text-center">
            <span className="text-primary">
              <BellIcon size={32} />
            </span>
            <p className="m-0 mt-3 font-semibold text-ink">Escolha um alerta</p>
            <p className="m-0 mt-1 max-w-sm text-sm text-muted">
              Cada alerta mostra o que disparou, o que a MarIA fez e tudo o que aconteceu depois. Os não revisados
              aparecem primeiro.
            </p>
          </div>
        )}
      </section>
    </div>
  );
}

function AlertView({ alertId, onChanged }) {
  const { refreshAlertCount } = usePanel();
  const navigate = useNavigate();
  const [alert, setAlert] = useState(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirmRelease, setConfirmRelease] = useState(false);
  const [error, setError] = useState("");

  const handleError = useCallback(
    (err) => {
      if (err.status === 404) navigate("/alertas", { replace: true });
      else setError(err.message);
    },
    [navigate]
  );

  // Abrir registra o "visto" (só a primeira vez entra na trilha); depois
  // relê de tempos em tempos, porque o e-mail sai em segundo plano.
  useEffect(() => {
    api
      .viewAlert(alertId)
      .then((data) => {
        setAlert(data);
        onChanged();
      })
      .catch(handleError);
    const id = setInterval(() => api.getAlert(alertId).then(setAlert).catch(handleError), REFRESH_MS);
    return () => clearInterval(id);
  }, [alertId, handleError, onChanged]);

  async function review() {
    setBusy(true);
    setError("");
    try {
      setAlert(await api.reviewAlert(alertId, note.trim()));
      setNote("");
      onChanged();
      refreshAlertCount();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function release() {
    setBusy(true);
    setError("");
    try {
      await api.releaseToBot(alert.conversation_id);
      setAlert(await api.getAlert(alertId));
      onChanged();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
      setConfirmRelease(false);
    }
  }

  if (!alert) {
    return (
      <div className="flex flex-1 items-center justify-center rounded-3xl border border-line bg-white text-sm text-muted">
        {error || "Carregando..."}
      </div>
    );
  }

  const paused = alert.conversation_state === "emergency_hold";

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto rounded-3xl border border-line bg-white">
      <header className="flex flex-wrap items-center gap-2 border-b border-line bg-[#f8faff] px-4 py-3 sm:px-6">
        <Link
          to="/alertas"
          className="-ml-1 flex rounded-xl p-1.5 text-slate no-underline hover:bg-[#eff4ff] lg:hidden"
          aria-label="Voltar para a lista"
        >
          <ArrowLeftIcon />
        </Link>
        <LevelTag level={alert.level} />
        <StatusTag alert={alert} />
        {alert.channel === "simulator" && <Tag>Teste</Tag>}
        <span className="ml-auto text-sm text-muted">{formatDateTime(alert.created_at)}</span>
      </header>

      <div className="space-y-6 px-4 py-5 sm:px-6">
        {/* O que disparou */}
        <section>
          {alert.excerpt && (
            <blockquote
              className={`m-0 rounded-2xl border-l-4 px-4 py-3 text-[17px] italic leading-relaxed text-ink ${
                alert.level === "emergency" ? "border-danger bg-danger-soft" : "border-warning bg-warning-soft"
              }`}
            >
              "{alert.excerpt}"
            </blockquote>
          )}
          {alert.trigger_text && <p className="m-0 mt-2 text-sm text-muted">{alert.trigger_text}</p>}
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <div className="min-w-0 flex-1">
              <p className="m-0 font-semibold text-ink">{alert.contact_name}</p>
              <p className="m-0 text-sm text-muted">
                {alert.channel === "simulator" ? "Simulador do painel" : `WhatsApp · ${alert.contact_phone}`}
              </p>
            </div>
            <Link
              to={`/conversas/${alert.conversation_id}`}
              className="flex items-center gap-2 rounded-2xl bg-primary px-4 py-2 text-sm font-semibold text-white no-underline hover:bg-primary-dark"
            >
              <ChatIcon size={18} /> Abrir conversa
            </Link>
          </div>
        </section>

        {paused && (
          <section className="rounded-2xl border border-[#fecaca] bg-danger-soft p-4">
            <div className="flex gap-3 text-danger">
              <AlertIcon size={20} className="mt-0.5 shrink-0" />
              <p className="m-0 text-sm">
                <strong>MarIA pausada nesta conversa.</strong> Nenhuma resposta automática sai até você liberar. Você
                pode escrever para a pessoa pela conversa.
              </p>
            </div>
            <div className="mt-3 flex flex-wrap items-center justify-end gap-2">
              {confirmRelease ? (
                <>
                  <span className="text-sm text-slate">A MarIA volta a responder nesta conversa. Liberar?</span>
                  <Button className="!px-3 !py-1.5 text-sm" disabled={busy} onClick={release}>
                    Sim
                  </Button>
                  <Button variant="ghost" className="!px-3 !py-1.5 text-sm" onClick={() => setConfirmRelease(false)}>
                    Não
                  </Button>
                </>
              ) : (
                <Button variant="soft" className="!px-4 !py-2 text-sm" onClick={() => setConfirmRelease(true)}>
                  Liberar a MarIA para responder
                </Button>
              )}
            </div>
          </section>
        )}

        {/* Trilha */}
        <section>
          <h2 className="m-0 text-lg font-semibold text-ink">Trilha do alerta</h2>
          <p className="m-0 mt-1 flex items-center gap-1.5 text-sm text-muted">
            <LockIcon size={14} /> O alerta e a trilha não podem ser editados nem apagados.
          </p>
          <ol className="m-0 mt-4 p-0">
            {alert.timeline.map((item, i) => (
              <li key={i} className="relative flex list-none gap-3 pb-5 last:pb-0">
                <span className="relative flex w-3 shrink-0 justify-center">
                  <span className={`mt-1.5 h-3 w-3 rounded-full ${DOTS[item.kind] || "bg-muted"}`} />
                  {(i < alert.timeline.length - 1 || alert.status === "new") && (
                    <span className="absolute top-5 bottom-[-4px] w-px bg-line" />
                  )}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="m-0 text-sm">
                    <span className="font-mono text-xs text-muted">{formatTime(item.at)}</span>
                    <span className="mx-2 font-semibold text-ink">{item.title}</span>
                    <span className="text-xs text-muted">{item.actor === "system" ? "Sistema" : "Você"}</span>
                  </p>
                  {item.detail && <p className="m-0 mt-0.5 text-sm leading-relaxed text-slate">{item.detail}</p>}
                </div>
              </li>
            ))}
            {alert.status === "new" && (
              <li className="flex list-none gap-3">
                <span className="flex w-3 shrink-0 justify-center">
                  <span className="mt-1.5 h-3 w-3 rounded-full border-2 border-warning bg-white" />
                </span>
                <p className="m-0 text-sm font-semibold text-[#92400e]">Pendente · sua revisão</p>
              </li>
            )}
          </ol>
        </section>

        {/* Revisão */}
        {alert.status === "new" ? (
          <section className="rounded-2xl bg-[#f8faff] p-4">
            <label className="block">
              <span className="font-semibold text-slate">Anotação da revisão (opcional)</span>
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                rows={2}
                maxLength={1000}
                placeholder="Ex.: liguei para a pessoa; a triagem exagerou; já é paciente..."
                className={inputClass}
              />
            </label>
            <p className="m-0 mt-2 text-xs text-muted">
              Não escreva dados clínicos aqui: a anotação fica na trilha, sem cifra.
            </p>
            <div className="mt-3 flex justify-end">
              <Button disabled={busy} onClick={review}>
                Marcar como revisado
              </Button>
            </div>
          </section>
        ) : (
          <p className="m-0 rounded-2xl bg-primary-soft px-4 py-3 text-sm text-primary">
            Revisado em {formatDateTime(alert.reviewed_at)}.
          </p>
        )}

        <ErrorBox>{error}</ErrorBox>
      </div>
    </div>
  );
}
