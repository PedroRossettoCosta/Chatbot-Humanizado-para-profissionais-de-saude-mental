import { TrashIcon } from "./icons.jsx";
import { inputClass } from "./ui.jsx";

// Grade semanal de intervalos (até 3 por dia), usada no horário de
// atendimento (Agenda). `DAYS` também serve aos dias especiais de cada cliente (Clientes). Mesmo
// formato do backend: {"mon": [{"start": "10:00", "end": "16:00"}], ...}.

export const DAYS = [
  { key: "mon", label: "Segunda" },
  { key: "tue", label: "Terça" },
  { key: "wed", label: "Quarta" },
  { key: "thu", label: "Quinta" },
  { key: "fri", label: "Sexta" },
  { key: "sat", label: "Sábado" },
  { key: "sun", label: "Domingo" },
];
const MAX_RANGES = 3;

// Todos os dias presentes, na ordem da semana; dia sem horário = lista vazia.
export function hoursFrom(value) {
  return Object.fromEntries(DAYS.map((d) => [d.key, (value?.[d.key] || []).map((r) => ({ ...r }))]));
}

export function problemIn(hours) {
  for (const { key, label } of DAYS) {
    const ranges = [...hours[key]].sort((a, b) => a.start.localeCompare(b.start));
    if (ranges.some((r) => !r.start || !r.end || r.start >= r.end)) return `${label}: o início precisa ser antes do fim.`;
    if (ranges.some((r, i) => i > 0 && ranges[i - 1].end > r.start)) return `${label}: os intervalos se sobrepõem.`;
  }
  return "";
}

// `newRange`: intervalo que aparece ao ligar um dia. `offLabel`: texto do
// dia desligado.
export default function WeeklyHours({ hours, onChangeDay, newRange, offLabel, addLabel }) {
  return (
    <ul className="m-0 divide-y divide-line p-0">
      {DAYS.map(({ key, label }) => {
        const ranges = hours[key];
        const on = ranges.length > 0;
        return (
          <li key={key} className="flex list-none flex-wrap items-start gap-x-4 gap-y-2 py-3">
            <label className="flex w-32 cursor-pointer items-center gap-3 pt-2.5 font-semibold text-slate">
              <input
                type="checkbox"
                className="h-5 w-5 cursor-pointer accent-[var(--color-primary)]"
                checked={on}
                onChange={(e) => onChangeDay(key, e.target.checked ? [{ ...newRange }] : [])}
              />
              {label}
            </label>
            <div className="min-w-0 flex-1 space-y-2">
              {!on && <p className="m-0 pt-2.5 text-sm text-muted">{offLabel}</p>}
              {ranges.map((range, i) => (
                <div key={i} className="flex flex-wrap items-center gap-2">
                  <input
                    type="time"
                    aria-label={`${label}: início`}
                    className={`${inputClass} mt-0 w-32 py-2`}
                    value={range.start}
                    onChange={(e) => onChangeDay(key, ranges.map((r, j) => (j === i ? { ...r, start: e.target.value } : r)))}
                  />
                  <span className="text-muted">às</span>
                  <input
                    type="time"
                    aria-label={`${label}: fim`}
                    className={`${inputClass} mt-0 w-32 py-2`}
                    value={range.end}
                    onChange={(e) => onChangeDay(key, ranges.map((r, j) => (j === i ? { ...r, end: e.target.value } : r)))}
                  />
                  <button
                    type="button"
                    onClick={() => onChangeDay(key, ranges.filter((_, j) => j !== i))}
                    className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-xl border-0 bg-transparent text-muted transition-colors hover:bg-danger-soft hover:text-danger"
                    aria-label={`Remover intervalo de ${label}`}
                    title="Remover intervalo"
                  >
                    <TrashIcon size={18} />
                  </button>
                </div>
              ))}
              {on && ranges.length < MAX_RANGES && (
                <button
                  type="button"
                  onClick={() => {
                    const last = ranges[ranges.length - 1];
                    onChangeDay(key, [...ranges, { start: last.end, end: last.end < "20:00" ? "20:00" : "23:59" }]);
                  }}
                  className="cursor-pointer border-0 bg-transparent p-0 text-sm font-semibold text-primary hover:underline"
                >
                  {addLabel}
                </button>
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
