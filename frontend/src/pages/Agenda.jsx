import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api.js";
import { CalendarIcon, RefreshIcon } from "../components/icons.jsx";
import { Button, ErrorBox, Field, Tag, formatDateTime, inputClass } from "../components/ui.jsx";
import WeeklyHours, { hoursFrom, problemIn } from "../components/WeeklyHours.jsx";
import { loadGoogle } from "../google.js";
import { usePanel } from "../panel/PanelContext.jsx";
import WeekCalendar from "./agenda/WeekCalendar.jsx";

const NEW_RANGE = { start: "09:00", end: "18:00" };

function Card({ eyebrow, title, action, children }) {
  return (
    <section className="rounded-3xl border border-line bg-white p-6 shadow-sm sm:p-8">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="m-0 text-xs font-semibold tracking-wider text-primary">{eyebrow}</p>
          <h2 className="m-0 mt-1 text-2xl font-semibold tracking-tight text-ink">{title}</h2>
        </div>
        {action}
      </div>
      <div className="mt-6">{children}</div>
    </section>
  );
}

const TABS = [
  { key: "pending", label: "Aguardando", test: (a) => a.awaiting_decision },
  { key: "confirmed", label: "Confirmados", test: (a) => a.status === "confirmed" && !a.awaiting_decision },
  { key: "closed", label: "Recusados e expirados", test: (a) => a.status === "rejected" || a.status === "expired" },
];

const STATUS_TAG = {
  tentative: ["warning", "Aguardando você"],
  confirmed: ["primary", "✓ Confirmado"],
  rejected: ["neutral", "Recusado"],
  expired: ["neutral", "Expirou sem decisão"],
};

function hoursLeft(iso) {
  const hours = Math.max(0, Math.round((new Date(iso).getTime() - Date.now()) / 3600000));
  return hours <= 1 ? "menos de 1 hora" : `${hours} horas`;
}

// "terça, 29/09 às 10:00" → [["terça, 29/09", ["10:00", ...]], ...]
function groupSlots(slots) {
  const days = new Map();
  for (const s of slots) {
    const [day, time] = s.label.split(" às ");
    if (!days.has(day)) days.set(day, []);
    days.get(day).push(time);
  }
  return [...days.entries()];
}

function capitalize(text) {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

// O que a pessoa pediu, no quadro à direita do cartão.
function RequestBox({ item }) {
  if (item.kind === "reschedule")
    return (
      <div className="rounded-2xl bg-[#eff4ff] px-4 py-3">
        <p className="m-0 text-xs font-semibold tracking-wider text-muted">TROCA DE HORÁRIO</p>
        <p className="m-0 mt-1 text-sm text-muted line-through">{capitalize(item.replaces_label || "")}</p>
        <p className="m-0 font-semibold text-ink">{capitalize(item.label)}</p>
      </div>
    );
  return (
    <div className={`rounded-2xl px-4 py-3 ${item.kind === "cancel" && item.awaiting_decision ? "bg-danger-soft" : "bg-[#eff4ff]"}`}>
      <p className="m-0 text-xs font-semibold tracking-wider text-muted">
        {item.kind === "cancel" && item.awaiting_decision ? "CANCELAMENTO PEDIDO" : "HORÁRIO PEDIDO"}
      </p>
      <p className="m-0 mt-1 font-semibold text-ink">{capitalize(item.label)}</p>
    </div>
  );
}

// Um pedido de horário (novo, troca ou cancelamento): quem, quando, e
// confirmar ou recusar.
function AppointmentCard({ item, busy, onDecide }) {
  const cancelAsked = item.kind === "cancel" && item.awaiting_decision;
  const [tone, label] = cancelAsked
    ? ["danger", "Pediu cancelamento"]
    : item.kind === "reschedule" && item.status === "tentative"
      ? ["warning", "Pediu troca"]
      : STATUS_TAG[item.status] || ["neutral", item.status];
  return (
    <li className="list-none rounded-3xl border border-line bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="m-0 text-lg font-semibold text-ink">{item.patient_name || "Sem nome"}</p>
            <Tag tone={item.channel === "whatsapp" ? "primary" : "info"}>
              {item.source === "panel" ? "Marcada por você" : item.channel === "whatsapp" ? "WhatsApp" : "Teste"}
            </Tag>
            <Tag tone={tone}>{label}</Tag>
          </div>
          {item.contact_phone && <p className="m-0 mt-1 text-sm text-muted">{item.contact_phone}</p>}
          <p className="m-0 mt-1 text-xs text-muted">
            {item.source === "panel" ? "Marcada pelo painel" : "Pedido pela SelenIA"} em {formatDateTime(item.created_at)}
          </p>
        </div>
        <RequestBox item={item} />
      </div>

      {cancelAsked ? (
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <span className="flex-1 text-sm text-muted">A sessão continua marcada até você decidir.</span>
          <Link to={`/conversas/${item.conversation_id}`} className="text-sm font-semibold text-primary">
            Ver conversa →
          </Link>
          <Button variant="ghost" onClick={() => onDecide(item, "reject")} disabled={busy}>
            Manter sessão
          </Button>
          <Button onClick={() => onDecide(item, "approve")} disabled={busy}>
            Confirmar cancelamento
          </Button>
        </div>
      ) : item.status === "tentative" ? (
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <span className="flex-1 text-sm text-muted">
            O horário está segurado na sua agenda por mais {hoursLeft(item.expires_at)}.
            {item.kind === "reschedule" && " Ao confirmar, a sessão antiga sai da agenda; ao recusar, ela continua."}
          </span>
          <Link to={`/conversas/${item.conversation_id}`} className="text-sm font-semibold text-primary">
            Ver conversa →
          </Link>
          <Button variant="ghost" onClick={() => onDecide(item, "reject")} disabled={busy}>
            Recusar
          </Button>
          <Button onClick={() => onDecide(item, "approve")} disabled={busy}>
            {item.kind === "reschedule" ? "✓ Confirmar troca" : "✓ Confirmar horário"}
          </Button>
        </div>
      ) : (
        <div className="mt-4 flex flex-wrap items-center gap-3 text-sm text-muted">
          <span className="flex-1">
            {item.status === "expired" &&
              "Ninguém decidiu em 24 horas; o horário foi liberado e a pessoa não foi avisada."}
            {item.source === "panel" && "Marcada por você no calendário."}
            {item.source !== "panel" &&
              (item.status === "confirmed" || item.status === "rejected") &&
              (item.contact_notified
                ? "A pessoa foi avisada pela conversa."
                : "A pessoa não pôde ser avisada automaticamente (janela de 24h do WhatsApp fechada). Avise pela conversa ou por telefone.")}
          </span>
          {item.conversation_id && (
            <Link to={`/conversas/${item.conversation_id}`} className="font-semibold text-primary">
              Ver conversa →
            </Link>
          )}
        </div>
      )}
    </li>
  );
}

// Agenda (protótipo: agenda_maria). A profissional conecta o Google
// Agenda e diz quando atende; a SelenIA cruza os dois para oferecer
// horários livres e reserva provisoriamente o que a pessoa escolher.
// Nada fica confirmado sem ela.
export default function Agenda() {
  const { professional, setProfessional, refreshAppointmentCount } = usePanel();
  const [requests, setRequests] = useState(null);
  const [tab, setTab] = useState("pending");
  // Aba da página: calendário, pedidos ou configuração.
  const [view, setView] = useState(null);
  const [maxPerDay, setMaxPerDay] = useState(() => (professional.max_sessions_per_day ? String(professional.max_sessions_per_day) : ""));
  const [deciding, setDeciding] = useState(null);
  const [status, setStatus] = useState(null);
  const [hours, setHours] = useState(() => hoursFrom(professional.working_hours));
  const [slots, setSlots] = useState(null);
  const [slotsError, setSlotsError] = useState("");
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  const slug = professional.slug;
  const original = useMemo(() => hoursFrom(professional.working_hours), [professional]);
  const originalMax = professional.max_sessions_per_day ? String(professional.max_sessions_per_day) : "";
  const dirty = JSON.stringify(hours) !== JSON.stringify(original) || maxPerDay !== originalMax;
  const maxNumber = Number(maxPerDay);
  const problem =
    problemIn(hours) ||
    (maxPerDay && !(Number.isInteger(maxNumber) && maxNumber >= 1 && maxNumber <= 20)
      ? "O limite de sessões por dia vai de 1 a 20 (ou vazio, sem limite)."
      : "");
  const hasHours = Object.values(original).some((r) => r.length);

  const loadSlots = useCallback(() => {
    setLoadingSlots(true);
    api
      .getFreeSlots(slug)
      .then((list) => {
        setSlots(list);
        setSlotsError("");
      })
      .catch((err) => {
        setSlots(null);
        setSlotsError(err.message);
      })
      .finally(() => setLoadingSlots(false));
  }, [slug]);

  const loadStatus = useCallback(
    () =>
      api
        .getCalendar(slug)
        .then((s) => {
          setStatus(s);
          setView((current) => current || (s.connected && s.events_permission ? "calendar" : "settings"));
          if (s.ready) loadSlots();
          else setSlots(null);
        })
        .catch((err) => setError(err.message)),
    [slug, loadSlots]
  );

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  const loadRequests = useCallback(
    () =>
      api
        .listAppointments(slug)
        .then(setRequests)
        .catch((err) => setError(err.message)),
    [slug]
  );

  useEffect(() => {
    loadRequests();
    const id = setInterval(loadRequests, 30000);
    return () => clearInterval(id);
  }, [loadRequests]);

  async function decide(item, action) {
    const question =
      item.kind === "cancel" && item.awaiting_decision
        ? action === "approve"
          ? `Cancelar a sessão de ${item.label}? Ela sai da sua agenda e a pessoa recebe um aviso.`
          : null
        : action === "reject"
          ? item.kind === "reschedule"
            ? `Recusar a troca para ${item.label}? A sessão antiga continua marcada e a pessoa recebe um aviso.`
            : `Recusar ${item.label}? A pessoa recebe um aviso e o horário sai da sua agenda.`
          : null;
    if (question && !window.confirm(question)) return;
    setDeciding(item.id);
    setError("");
    try {
      if (action === "approve") await api.approveAppointment(item.id);
      else await api.rejectAppointment(item.id);
    } catch (err) {
      setError(err.message);
    } finally {
      setDeciding(null);
      loadRequests();
      refreshAppointmentCount();
      if (status?.ready) loadSlots();
    }
  }

  async function syncWithGoogle() {
    setError("");
    setConnecting(true);
    try {
      const [{ google_client_id: clientId }, google] = await Promise.all([api.getAuthConfig(), loadGoogle()]);
      const client = google.accounts.oauth2.initCodeClient({
        client_id: clientId,
        scope: status.requested_scopes,
        ux_mode: "popup",
        callback: async (response) => {
          if (response.error) {
            setError("O Google não liberou o acesso à agenda.");
            setConnecting(false);
            return;
          }
          try {
            const updated = await api.connectCalendar(slug, response.code);
            setStatus(updated);
            if (updated.ready) loadSlots();
          } catch (err) {
            setError(err.message);
          } finally {
            setConnecting(false);
          }
        },
        // Janela fechada ou bloqueada pelo navegador.
        error_callback: (err) => {
          if (err.type === "popup_failed_to_open") setError("O navegador bloqueou a janela do Google. Libere pop-ups para este endereço.");
          setConnecting(false);
        },
      });
      client.requestCode();
    } catch (err) {
      setError(err.message);
      setConnecting(false);
    }
  }

  async function disconnect() {
    if (!window.confirm("Desconectar a agenda? A SelenIA deixa de ver seus horários livres.")) return;
    setError("");
    try {
      setStatus(await api.disconnectCalendar(slug));
      setSlots(null);
    } catch (err) {
      setError(err.message);
    }
  }

  async function saveHours() {
    setSaving(true);
    setError("");
    try {
      const updated = await api.updateProfessional(slug, {
        working_hours: hours,
        max_sessions_per_day: maxPerDay ? maxNumber : null,
      });
      setProfessional(updated);
      setHours(hoursFrom(updated.working_hours));
      setMaxPerDay(updated.max_sessions_per_day ? String(updated.max_sessions_per_day) : "");
      setSaved(true);
      loadStatus();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  function changeDay(key, ranges) {
    setSaved(false);
    setHours((prev) => ({ ...prev, [key]: ranges }));
  }

  if (!status) return <p className="text-muted">{error || "Carregando..."}</p>;
  const visibleTab = TABS.find((t) => t.key === tab);
  const pendingCount = (requests || []).filter(TABS[0].test).length;

  return (
    <div className="mx-auto max-w-6xl pb-12">
      <p className="m-0 text-xs font-semibold tracking-wider text-primary">GOOGLE AGENDA</p>
      <h1 className="m-0 mt-2 text-4xl font-bold tracking-tight text-ink">Agenda</h1>
      <p className="m-0 mt-2 max-w-2xl text-muted">
        A SelenIA consulta sua agenda para oferecer horários livres a quem quer marcar. Nada é confirmado sem você.
      </p>

      <div className="mt-6 flex flex-wrap gap-2 border-b border-line pb-3">
        {[
          ["calendar", "Calendário"],
          ["requests", `Pedidos de horário${pendingCount ? ` (${pendingCount})` : ""}`],
          ["settings", "Configurar"],
        ].map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setView(key)}
            className={`cursor-pointer rounded-2xl border-0 px-4 py-2.5 text-[15px] font-semibold ${
              view === key ? "bg-primary text-white" : "bg-transparent text-slate hover:bg-primary-soft"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {error && (
        <div className="mt-6">
          <ErrorBox>{error}</ErrorBox>
        </div>
      )}

      {view === "calendar" && (
        <div className="mt-6">
          {status.connected && status.events_permission ? (
            <WeekCalendar
              slug={slug}
              workingHours={professional.working_hours}
              sessionMinutes={professional.session_minutes}
              onChanged={() => {
                loadRequests();
                refreshAppointmentCount();
                if (status.ready) loadSlots();
              }}
            />
          ) : (
            <p className="m-0 rounded-3xl border border-dashed border-line px-5 py-6 text-sm text-muted">
              Para ver e marcar na agenda aqui, conecte o Google Agenda com a permissão de eventos em{" "}
              <button type="button" onClick={() => setView("settings")} className="cursor-pointer border-0 bg-transparent p-0 font-semibold text-primary">
                Configurar
              </button>
              .
            </p>
          )}
        </div>
      )}

      {view === "requests" && (
      <section className="mt-6">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="m-0 mr-2 text-2xl font-semibold tracking-tight text-ink">Pedidos de horário</h2>
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setTab(t.key)}
              className={`cursor-pointer whitespace-nowrap rounded-full border-0 px-4 py-2 text-sm ${
                tab === t.key ? "bg-primary text-white" : "bg-[#eff4ff] text-slate hover:bg-primary-soft"
              }`}
            >
              {t.label} ({(requests || []).filter(t.test).length})
            </button>
          ))}
        </div>
        <ul className="m-0 mt-4 space-y-4 p-0">
          {requests && requests.filter(visibleTab.test).length === 0 && (
            <li className="list-none rounded-3xl border border-dashed border-line px-5 py-6 text-sm text-muted">
              {tab !== "pending"
                ? "Nada por aqui ainda."
                : status.events_permission
                  ? "Nenhum pedido aguardando. Quando alguém escolher um horário na conversa, ele aparece aqui."
                  : "A SelenIA ainda não reserva horários: conecte a agenda com a permissão de criar eventos."}
            </li>
          )}
          {(requests || []).filter(visibleTab.test).map((item) => (
            <AppointmentCard key={item.id} item={item} busy={deciding === item.id} onDecide={decide} />
          ))}
        </ul>
      </section>
      )}

      {view === "settings" && (
      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_360px] [&>*]:min-w-0">
        <div className="space-y-6">
          <Card eyebrow="GOOGLE AGENDA" title={status.connected ? "Agenda conectada" : "Conectar sua agenda"}>
            <div className="flex flex-wrap items-start gap-4">
              <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-primary-soft text-primary">
                <CalendarIcon />
              </span>
              <div className="min-w-0 flex-1">
                {status.connected ? (
                  <>
                    <p className="m-0 break-all text-lg font-semibold text-primary">{status.google_email}</p>
                    <div className="mt-1 flex flex-wrap items-center gap-2">
                      {!status.ready ? (
                        <Tag tone="warning">Falta o horário de atendimento</Tag>
                      ) : status.can_book ? (
                        <Tag tone="primary">✓ Consulta e reserva ativas</Tag>
                      ) : (
                        <Tag tone="warning">Só consulta: falta a permissão de reservar</Tag>
                      )}
                      <span className="text-xs text-muted">desde {formatDateTime(status.connected_at)}</span>
                    </div>
                  </>
                ) : (
                  <p className="m-0 text-slate">
                    Ao sincronizar, o Google pede sua permissão numa janela. Use a conta da agenda em que você marca as
                    sessões.
                  </p>
                )}
                <p className="m-0 mt-3 text-sm leading-relaxed text-muted">
                  🔒 A SelenIA vê só se cada horário está livre ou ocupado: o nome, a descrição e os participantes dos seus
                  eventos não chegam até ela. Ela só cria e altera os eventos "Sessão (a confirmar)" que ela mesma
                  reserva.
                </p>
                {status.connected && !status.events_permission && (
                  <p className="m-0 mt-3 rounded-2xl bg-warning-soft px-4 py-3 text-sm text-[#92400e]">
                    Para a SelenIA reservar horários, clique em <strong>Permitir reservas</strong> e marque, na janela do
                    Google, a permissão de ver e editar eventos.
                  </p>
                )}
              </div>
            </div>

            <div className="mt-6 flex flex-wrap gap-3">
              {!status.configured ? (
                <p className="m-0 text-sm text-danger">
                  A agenda ainda não foi configurada no servidor (falta o GOOGLE_CLIENT_SECRET).
                </p>
              ) : status.connected ? (
                <>
                  {!status.events_permission && (
                    <Button onClick={syncWithGoogle} disabled={connecting}>
                      {connecting ? "Aguardando o Google..." : "Permitir reservas"}
                    </Button>
                  )}
                  <Button variant="soft" onClick={syncWithGoogle} disabled={connecting}>
                    {connecting ? "Aguardando o Google..." : "Trocar de conta"}
                  </Button>
                  <Button variant="ghost" onClick={disconnect}>
                    Desconectar
                  </Button>
                </>
              ) : (
                <Button onClick={syncWithGoogle} disabled={connecting}>
                  {connecting ? "Aguardando o Google..." : "Sincronizar com o Google Agenda"}
                </Button>
              )}
            </div>
          </Card>

          <Card eyebrow="QUANDO VOCÊ ATENDE" title="Horário de atendimento">
            <p className="m-0 text-sm text-muted">
              A SelenIA só oferece horários dentro destes intervalos (horário de Brasília). Sessões de{" "}
              <strong className="text-slate">{professional.session_minutes} minutos</strong>, definidas no{" "}
              <Link to="/perfil" className="text-primary">
                Perfil do atendimento
              </Link>
              .
            </p>
            <div className="mt-5">
              <WeeklyHours
                hours={hours}
                onChangeDay={changeDay}
                newRange={NEW_RANGE}
                offLabel="Não atende"
                addLabel="+ Intervalo (ex.: depois do almoço)"
              />
            </div>
            <div className="mt-5 rounded-2xl bg-[#eff4ff] p-4">
              <Field
                label="Máximo de sessões por dia"
                hint="Quantas sessões a SelenIA pode deixar marcadas num mesmo dia (pedidos aguardando, confirmadas e as que você marca pelo calendário). Não vale para os clientes especiais (tela Clientes). Vazio = sem limite."
              >
                <input
                  type="number"
                  min={1}
                  max={20}
                  placeholder="Sem limite"
                  className={`${inputClass} max-w-40`}
                  value={maxPerDay}
                  onChange={(e) => {
                    setSaved(false);
                    setMaxPerDay(e.target.value);
                  }}
                />
              </Field>
            </div>
            <div className="mt-6 flex flex-wrap items-center gap-3">
              <Button onClick={saveHours} disabled={!dirty || saving || Boolean(problem)}>
                {saving ? "Salvando..." : "Salvar horário"}
              </Button>
              {dirty && (
                <Button
                  variant="ghost"
                  onClick={() => {
                    setHours(original);
                    setMaxPerDay(originalMax);
                  }}
                >
                  Descartar
                </Button>
              )}
              {problem && <span className="text-sm text-danger">{problem}</span>}
              {!dirty && saved && <span className="text-sm font-semibold text-primary">✓ Horário salvo</span>}
            </div>
          </Card>
        </div>

        <aside className="lg:sticky lg:top-24 lg:self-start">
          <Card
            eyebrow="PRÉVIA"
            title="O que a SelenIA vê agora"
            action={
              status.ready && (
                <button
                  type="button"
                  onClick={loadSlots}
                  disabled={loadingSlots}
                  className="flex h-10 w-10 cursor-pointer items-center justify-center rounded-xl border-0 bg-transparent text-muted hover:bg-primary-soft hover:text-primary disabled:opacity-50"
                  aria-label="Atualizar horários"
                  title="Atualizar"
                >
                  <RefreshIcon />
                </button>
              )
            }
          >
            {!status.ready ? (
              <ul className="m-0 space-y-2 pl-5 text-sm text-muted">
                <li className={status.connected ? "line-through" : ""}>Conecte o Google Agenda</li>
                <li className={hasHours ? "line-through" : ""}>Preencha e salve o horário de atendimento</li>
              </ul>
            ) : slotsError ? (
              <ErrorBox>{slotsError}</ErrorBox>
            ) : !slots ? (
              <p className="m-0 text-sm text-muted">Consultando a agenda...</p>
            ) : slots.length === 0 ? (
              <p className="m-0 text-sm text-muted">Nenhum horário livre nas próximas duas semanas.</p>
            ) : (
              <>
                <p className="m-0 mb-3 text-sm text-muted">
                  Onde cabe uma sessão de {professional.session_minutes} minutos nas próximas duas semanas, de meia em
                  meia hora, com pelo menos 12 horas de antecedência. Na conversa, a SelenIA oferece até 3 de cada vez.
                </p>
                <ul className="m-0 max-h-[60vh] space-y-3 overflow-y-auto p-0">
                  {groupSlots(slots).map(([day, times]) => (
                    <li key={day} className="list-none">
                      <p className="m-0 text-sm font-semibold text-ink">{capitalize(day)}</p>
                      <div className="mt-1 flex flex-wrap gap-1.5">
                        {times.map((t) => (
                          <span key={t} className="rounded-lg bg-[#eff4ff] px-2 py-1 text-xs text-slate">
                            {t}
                          </span>
                        ))}
                      </div>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </Card>
        </aside>
      </div>
      )}
    </div>
  );
}
