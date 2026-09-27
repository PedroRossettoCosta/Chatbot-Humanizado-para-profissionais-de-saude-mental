// Peças visuais comuns do painel, no estilo do protótipo (Serene Sanctuary).

export const inputClass =
  "mt-2 w-full rounded-2xl border border-line bg-white px-4 py-3 text-base text-ink outline-none " +
  "placeholder:text-muted/70 focus:border-primary focus:ring-4 focus:ring-primary/15";

export function Field({ label, required, hint, children }) {
  return (
    <label className="block">
      <span className="font-semibold text-slate">
        {label} {required && <span className="text-danger">*</span>}
      </span>
      {children}
      {hint && <span className="mt-2 block text-sm text-muted">{hint}</span>}
    </label>
  );
}

const buttonStyles = {
  primary: "border-0 bg-primary text-white hover:bg-primary-dark",
  soft: "border-0 bg-primary-soft text-primary hover:bg-[#dfeae1]",
  ghost: "border-0 bg-transparent text-slate hover:bg-canvas",
};

export function Button({ variant = "primary", className = "", ...props }) {
  return (
    <button
      type="button"
      className={`cursor-pointer rounded-2xl px-6 py-3 text-base font-semibold disabled:cursor-not-allowed disabled:opacity-50 ${buttonStyles[variant]} ${className}`}
      {...props}
    />
  );
}

export function ErrorBox({ children }) {
  if (!children) return null;
  return (
    <div className="rounded-2xl bg-danger-soft px-4 py-3 text-sm text-danger" role="alert">
      {children}
    </div>
  );
}

// Horário de Brasília, que é como a profissional lê.
export function formatDateTime(iso) {
  return new Date(iso).toLocaleString("pt-BR", {
    timeZone: TZ,
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// Etiquetas e horários das listas (Conversas, Alertas).
const TZ = "America/Sao_Paulo";

export const TONES = {
  neutral: "bg-[#eff4ff] text-slate",
  info: "bg-[#dce9ff] text-[#1e40af]",
  warning: "bg-warning-soft text-[#92400e]",
  danger: "bg-danger-soft text-danger",
  primary: "bg-primary-soft text-primary",
};

export function Tag({ tone = "neutral", children }) {
  return (
    <span className={`whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium ${TONES[tone]}`}>{children}</span>
  );
}

export function dayKey(date) {
  return date.toLocaleDateString("en-CA", { timeZone: TZ });
}

export function formatTime(iso) {
  return new Date(iso).toLocaleTimeString("pt-BR", { timeZone: TZ, hour: "2-digit", minute: "2-digit" });
}

// "14:32" hoje, "Ontem", ou "24/09".
export function shortWhen(iso) {
  const date = new Date(iso);
  const today = new Date();
  const yesterday = new Date(today.getTime() - 86400000);
  if (dayKey(date) === dayKey(today)) return formatTime(iso);
  if (dayKey(date) === dayKey(yesterday)) return "Ontem";
  return date.toLocaleDateString("pt-BR", { timeZone: TZ, day: "2-digit", month: "2-digit" });
}

export function dayLabel(iso) {
  const date = new Date(iso);
  const today = new Date();
  if (dayKey(date) === dayKey(today)) return "Hoje";
  if (dayKey(date) === dayKey(new Date(today.getTime() - 86400000))) return "Ontem";
  return date.toLocaleDateString("pt-BR", { timeZone: TZ, day: "numeric", month: "long" });
}
