import { useEffect, useRef, useState } from "react";

import { ChevronDownIcon } from "./icons.jsx";
import { inputClass } from "./ui.jsx";

// Lista suspensa de escolha múltipla: o botão mostra o que está marcado e
// abre as opções com caixas de seleção. `options` = [{ key, label }];
// `value` = lista de chaves marcadas, na ordem de `options`.
export default function MultiSelect({ options, value, onChange, placeholder, ariaLabel }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  // Fecha ao clicar fora ou apertar Esc.
  useEffect(() => {
    if (!open) return undefined;
    const onClick = (e) => ref.current && !ref.current.contains(e.target) && setOpen(false);
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const selected = options.filter((o) => value.includes(o.key));
  const toggle = (key) => {
    const next = value.includes(key) ? value.filter((k) => k !== key) : [...value, key];
    onChange(options.map((o) => o.key).filter((k) => next.includes(k)));
  };

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-label={ariaLabel}
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className={`${inputClass} flex cursor-pointer items-center gap-2 text-left`}
      >
        <span className={`flex-1 truncate ${selected.length ? "text-ink" : "text-muted/70"}`}>
          {selected.length ? selected.map((o) => o.label).join(", ") : placeholder}
        </span>
        <ChevronDownIcon size={18} className={`shrink-0 text-muted transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <ul className="absolute z-20 m-0 mt-2 w-full rounded-2xl border border-line bg-white p-2 shadow-xl">
          {options.map((o) => (
            <li key={o.key} className="list-none">
              <label className="flex cursor-pointer items-center gap-3 rounded-xl px-3 py-2.5 text-slate hover:bg-primary-soft">
                <input
                  type="checkbox"
                  className="h-5 w-5 cursor-pointer accent-[var(--color-primary)]"
                  checked={value.includes(o.key)}
                  onChange={() => toggle(o.key)}
                />
                {o.label}
              </label>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
