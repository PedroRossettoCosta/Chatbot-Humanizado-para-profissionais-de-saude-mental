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
    timeZone: "America/Sao_Paulo",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
