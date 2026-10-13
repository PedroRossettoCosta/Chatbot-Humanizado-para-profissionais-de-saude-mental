import { useCallback, useEffect, useMemo, useState } from "react";

import { api } from "../../api.js";
import { CloseIcon } from "../../components/icons.jsx";
import { Button, ErrorBox, Field, inputClass } from "../../components/ui.jsx";

const TZ = "America/Sao_Paulo";
const HOUR_PX = 48;
const DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
const DAY_SHORT = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"];

// Datas como "AAAA-MM-DD" no fuso da agenda, e contas de dias em UTC
// para não escorregar com o fuso do navegador.
const partsFormat = new Intl.DateTimeFormat("en-CA", {
  timeZone: TZ,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

function localParts(value) {
  const p = Object.fromEntries(partsFormat.formatToParts(new Date(value)).map((x) => [x.type, x.value]));
  return { ymd: `${p.year}-${p.month}-${p.day}`, minutes: Number(p.hour) * 60 + Number(p.minute) };
}

function addDays(ymd, n) {
  const [y, m, d] = ymd.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d + n)).toISOString().slice(0, 10);
}

function weekday(ymd) {
  const [y, m, d] = ymd.split("-").map(Number);
  return (new Date(Date.UTC(y, m - 1, d)).getUTCDay() + 6) % 7; // 0 = segunda
}

function mondayOf(ymd) {
  return addDays(ymd, -weekday(ymd));
}

function toMinutes(hhmm) {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
}

function hhmm(minutes) {
  return `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;
}

function dm(ymd) {
  return `${ymd.slice(8, 10)}/${ymd.slice(5, 7)}`;
}

const STYLE = {
  maria_tentative: "border-l-4 border-warning bg-warning-soft text-[#92400e]",
  maria_confirmed: "border-l-4 border-primary bg-primary-soft text-primary-dark",
  google: "border-l-4 border-[#94a3b8] bg-[#eef2f7] text-slate",
};

// Eventos que se sobrepõem no mesmo dia ficam lado a lado.
function withLanes(items) {
  const sorted = [...items].sort((a, b) => a.start - b.start || b.end - a.end);
  const lanesEnd = [];
  for (const item of sorted) {
    let lane = lanesEnd.findIndex((end) => end <= item.start);
    if (lane === -1) lane = lanesEnd.length;
    lanesEnd[lane] = item.end;
    item.lane = lane;
  }
  for (const item of sorted) {
    const overlapping = sorted.filter((o) => o.start < item.end && item.start < o.end);
    item.lanes = Math.max(...overlapping.map((o) => o.lane)) + 1;
  }
  return sorted;
}

function NewEventDialog({ initial, sessionMinutes, onClose, onSave }) {
  const [form, setForm] = useState(() => ({
    kind: "session",
    title: "",
    date: initial.date,
    time: initial.time,
    minutes: String(sessionMinutes || 50),
  }));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const set = (field) => (e) => setForm((prev) => ({ ...prev, [field]: e.target.value }));
  const minutes = Number(form.minutes);
  const valid = form.title.trim() && form.date && form.time && Number.isInteger(minutes) && minutes >= 5 && minutes <= 720;

  async function submit(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await onSave({ kind: form.kind, title: form.title.trim(), starts_at: `${form.date}T${form.time}`, minutes });
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-ink/30 p-4 sm:items-center" onClick={onClose}>
      <form
        onSubmit={submit}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl"
      >
        <div className="flex items-center justify-between">
          <h3 className="m-0 text-xl font-semibold text-ink">Marcar na agenda</h3>
          <button
            type="button"
            onClick={onClose}
            className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-xl border-0 bg-transparent text-muted hover:bg-canvas"
            aria-label="Fechar"
          >
            <CloseIcon />
          </button>
        </div>

        <div className="mt-4 flex gap-2">
          {[
            ["session", "Sessão"],
            ["block", "Outro compromisso"],
          ].map(([key, label]) => (
            <button
              key={key}
              type="button"
              onClick={() =>
                setForm((prev) => ({ ...prev, kind: key, minutes: key === "session" ? String(sessionMinutes || 50) : "60" }))
              }
              className={`flex-1 cursor-pointer rounded-2xl border-0 px-3 py-2.5 text-sm font-semibold ${
                form.kind === key ? "bg-primary text-white" : "bg-[#eff4ff] text-slate hover:bg-primary-soft"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="mt-5 space-y-4">
          <Field
            label={form.kind === "session" ? "Nome da pessoa" : "Título"}
            required
            hint={form.kind === "session" ? "Vai para o Google Agenda como “Sessão · nome”." : "Ex.: supervisão, almoço, curso."}
          >
            <input className={inputClass} value={form.title} onChange={set("title")} maxLength={120} autoFocus />
          </Field>
          <div className="grid grid-cols-2 gap-3 [&>*]:min-w-0">
            <Field label="Data" required>
              <input type="date" className={inputClass} value={form.date} onChange={set("date")} />
            </Field>
            <Field label="Início" required>
              <input type="time" className={inputClass} value={form.time} onChange={set("time")} />
            </Field>
          </div>
          <Field label="Duração (minutos)" required>
            <input type="number" min={5} max={720} className={`${inputClass} max-w-32`} value={form.minutes} onChange={set("minutes")} />
          </Field>
        </div>

        {error && (
          <div className="mt-4">
            <ErrorBox>{error}</ErrorBox>
          </div>
        )}
        <div className="mt-6 flex justify-end gap-3">
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" disabled={!valid || saving}>
            {saving ? "Marcando..." : "Marcar no Google Agenda"}
          </Button>
        </div>
      </form>
    </div>
  );
}

// Calendário da semana: eventos do Google Agenda (com título, só para a
// profissional), sessões da SelenIA e o horário de atendimento. Clicar num
// espaço vazio abre "Marcar na agenda" naquele horário.
export default function WeekCalendar({ slug, workingHours, sessionMinutes, onChanged }) {
  const today = localParts(Date.now()).ymd;
  const [weekStart, setWeekStart] = useState(() => mondayOf(today));
  const [events, setEvents] = useState(null);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(null);

  const days = useMemo(() => Array.from({ length: 7 }, (_, i) => addDays(weekStart, i)), [weekStart]);

  const load = useCallback(() => {
    setError("");
    api
      .getEvents(slug, weekStart)
      .then(setEvents)
      .catch((err) => {
        setEvents([]);
        setError(err.message);
      });
  }, [slug, weekStart]);

  useEffect(() => {
    load();
  }, [load]);

  // Faixa de horas: o horário de atendimento, alargado para caber os eventos.
  const timed = useMemo(
    () =>
      (events || [])
        .filter((e) => !e.all_day)
        .map((e) => {
          const s = localParts(e.starts_at);
          const f = localParts(e.ends_at);
          return { ...e, day: s.ymd, start: s.minutes, end: f.ymd === s.ymd ? Math.max(f.minutes, s.minutes + 15) : 24 * 60 };
        }),
    [events]
  );
  const [firstHour, lastHour] = useMemo(() => {
    let first = 8;
    let last = 19;
    for (const ranges of Object.values(workingHours || {})) {
      for (const r of ranges) {
        first = Math.min(first, Math.floor(toMinutes(r.start) / 60));
        last = Math.max(last, Math.ceil(toMinutes(r.end) / 60));
      }
    }
    for (const e of timed) {
      if (!days.includes(e.day)) continue;
      first = Math.min(first, Math.floor(e.start / 60));
      last = Math.max(last, Math.ceil(e.end / 60));
    }
    return [Math.max(0, first), Math.min(24, last)];
  }, [workingHours, timed, days]);
  const height = (lastHour - firstHour) * HOUR_PX;
  const y = (minutes) => ((minutes - firstHour * 60) / 60) * HOUR_PX;

  function openAt(day, event) {
    const rect = event.currentTarget.getBoundingClientRect();
    const minutes = firstHour * 60 + ((event.clientY - rect.top) / HOUR_PX) * 60;
    const rounded = Math.min(Math.floor(minutes / 30) * 30, 23 * 60 + 30);
    setCreating({ date: day, time: hhmm(rounded) });
  }

  async function save(payload) {
    await api.createEvent(slug, payload);
    setCreating(null);
    load();
    onChanged?.();
  }

  const lastDay = days[6];
  return (
    <section className="rounded-3xl border border-line bg-white p-4 shadow-sm sm:p-6">
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="soft" className="px-3 py-2" onClick={() => setWeekStart(addDays(weekStart, -7))} aria-label="Semana anterior">
          ‹
        </Button>
        <Button variant="soft" className="px-3 py-2" onClick={() => setWeekStart(addDays(weekStart, 7))} aria-label="Próxima semana">
          ›
        </Button>
        <Button variant="ghost" className="px-3 py-2" onClick={() => setWeekStart(mondayOf(today))}>
          Hoje
        </Button>
        <p className="m-0 flex-1 font-semibold text-ink">
          {dm(weekStart)} a {dm(lastDay)}/{lastDay.slice(0, 4)}
        </p>
        <Button onClick={() => setCreating({ date: today < weekStart || today > lastDay ? weekStart : today, time: "09:00" })}>
          + Marcar
        </Button>
      </div>

      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
        <span><span className="mr-1 inline-block h-3 w-3 rounded bg-warning-soft align-middle ring-1 ring-warning" /> A confirmar (pedido pela SelenIA)</span>
        <span><span className="mr-1 inline-block h-3 w-3 rounded bg-primary-soft align-middle ring-1 ring-primary" /> Sessão confirmada</span>
        <span><span className="mr-1 inline-block h-3 w-3 rounded bg-[#eef2f7] align-middle ring-1 ring-[#94a3b8]" /> Outros eventos</span>
        <span><span className="mr-1 inline-block h-3 w-3 rounded bg-white align-middle ring-1 ring-line" /> Horário de atendimento</span>
      </div>

      {error && (
        <div className="mt-3">
          <ErrorBox>{error}</ErrorBox>
        </div>
      )}

      <div className="mt-4 overflow-x-auto">
        <div className="min-w-[720px]">
          {/* Cabeçalho dos dias e eventos de dia inteiro */}
          <div className="grid grid-cols-[48px_repeat(7,1fr)] border-b border-line">
            <div />
            {days.map((day, i) => (
              <div key={day} className="px-1 pb-2 text-center">
                <p className={`m-0 text-xs uppercase ${day === today ? "font-bold text-primary" : "text-muted"}`}>{DAY_SHORT[i]}</p>
                <p className={`m-0 text-lg font-semibold ${day === today ? "text-primary" : "text-ink"}`}>{day.slice(8, 10)}</p>
                {(events || [])
                  .filter((e) => e.all_day && localParts(e.starts_at).ymd <= day && day < localParts(e.ends_at).ymd)
                  .map((e) => (
                    <p key={e.id} className={`m-0 mt-1 truncate rounded-md px-1.5 py-0.5 text-left text-[11px] ${STYLE[e.kind]}`} title={e.title}>
                      {e.title}
                    </p>
                  ))}
              </div>
            ))}
          </div>

          {/* Grade das horas */}
          <div className="grid grid-cols-[48px_repeat(7,1fr)]">
            <div className="relative" style={{ height }}>
              {Array.from({ length: lastHour - firstHour }, (_, i) => (
                <span key={i} className="absolute right-2 -translate-y-1/2 text-[11px] text-muted" style={{ top: i * HOUR_PX }}>
                  {i === 0 ? "" : `${firstHour + i}h`}
                </span>
              ))}
            </div>
            {days.map((day, i) => {
              const ranges = (workingHours || {})[DAY_KEYS[i]] || [];
              const dayEvents = withLanes(timed.filter((e) => e.day === day));
              return (
                <div
                  key={day}
                  className="relative cursor-pointer border-l border-line bg-[#f4f6fa]"
                  style={{ height }}
                  onClick={(e) => openAt(day, e)}
                  title="Clique para marcar neste horário"
                >
                  {ranges.map((r) => (
                    <div
                      key={r.start}
                      className="absolute inset-x-0 bg-white"
                      style={{ top: y(toMinutes(r.start)), height: y(toMinutes(r.end)) - y(toMinutes(r.start)) }}
                    />
                  ))}
                  {Array.from({ length: lastHour - firstHour }, (_, h) => (
                    <div key={h} className="pointer-events-none absolute inset-x-0 border-t border-line/70" style={{ top: h * HOUR_PX }} />
                  ))}
                  {dayEvents.map((e) => (
                    <div
                      key={e.id}
                      onClick={(ev) => ev.stopPropagation()}
                      className={`absolute overflow-hidden rounded-md px-1.5 py-0.5 text-[11px] leading-tight shadow-sm ${STYLE[e.kind]}`}
                      style={{
                        top: y(e.start) + 1,
                        height: Math.max(y(e.end) - y(e.start) - 2, 18),
                        left: `calc(${(e.lane / e.lanes) * 100}% + 2px)`,
                        width: `calc(${100 / e.lanes}% - 4px)`,
                      }}
                      title={`${hhmm(e.start)}–${hhmm(Math.min(e.end, 24 * 60 - 1))} ${e.title}`}
                    >
                      <p className="m-0 font-semibold">{hhmm(e.start)}</p>
                      <p className="m-0 truncate">{e.title}</p>
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      </div>
      {events === null && <p className="m-0 mt-3 text-sm text-muted">Carregando a agenda...</p>}

      {creating && (
        <NewEventDialog
          initial={creating}
          sessionMinutes={sessionMinutes}
          onClose={() => setCreating(null)}
          onSave={save}
        />
      )}
    </section>
  );
}
