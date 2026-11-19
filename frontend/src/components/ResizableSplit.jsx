import { useCallback, useEffect, useRef, useState } from "react";

// Lista à esquerda e detalhe à direita (Conversas, Alertas): no computador,
// a largura da lista se ajusta pelo divisor e fica lembrada neste
// navegador. Em tela dividida, o detalhe fica com o resto, nunca espremido.
const LIST_WIDTH_MIN = 240;
const DETAIL_MIN = 320;
const SPLITTER_SPACE = 24; // divisor + espaçamento entre as colunas

export function useListWidth(storageKey, defaultWidth) {
  const gridRef = useRef(null);
  const [width, setWidth] = useState(() => {
    try {
      const saved = Number(localStorage.getItem(storageKey));
      return saved >= LIST_WIDTH_MIN ? saved : defaultWidth;
    } catch {
      return defaultWidth;
    }
  });

  const clamp = useCallback((value) => {
    const total = gridRef.current?.clientWidth || window.innerWidth;
    const max = Math.max(LIST_WIDTH_MIN, total - DETAIL_MIN - SPLITTER_SPACE);
    return Math.round(Math.min(Math.max(value, LIST_WIDTH_MIN), max));
  }, []);

  const save = useCallback(
    (value) => {
      try {
        localStorage.setItem(storageKey, String(value));
      } catch {
        // Sem armazenamento (aba anônima, por exemplo): vale só nesta visita.
      }
    },
    [storageKey]
  );

  // Janela encolheu (tela dividida): o detalhe não pode ficar espremido.
  useEffect(() => {
    const fit = () => setWidth((w) => clamp(w));
    fit();
    window.addEventListener("resize", fit);
    return () => window.removeEventListener("resize", fit);
  }, [clamp]);

  const startDrag = useCallback(
    (event) => {
      event.preventDefault();
      const handle = event.currentTarget;
      handle.setPointerCapture(event.pointerId);
      const left = gridRef.current.getBoundingClientRect().left;
      let last = null;
      const move = (e) => {
        last = clamp(e.clientX - left);
        setWidth(last);
      };
      const end = () => {
        handle.removeEventListener("pointermove", move);
        handle.removeEventListener("pointerup", end);
        handle.removeEventListener("pointercancel", end);
        document.body.style.userSelect = "";
        if (last !== null) save(last);
      };
      document.body.style.userSelect = "none";
      handle.addEventListener("pointermove", move);
      handle.addEventListener("pointerup", end);
      handle.addEventListener("pointercancel", end);
    },
    [clamp, save]
  );

  const onKeyDown = useCallback(
    (event) => {
      const step = event.shiftKey ? 80 : 20;
      const delta = event.key === "ArrowLeft" ? -step : event.key === "ArrowRight" ? step : 0;
      if (!delta) return;
      event.preventDefault();
      setWidth((w) => {
        const next = clamp(w + delta);
        save(next);
        return next;
      });
    },
    [clamp, save]
  );

  const reset = useCallback(() => {
    const next = clamp(defaultWidth);
    setWidth(next);
    save(next);
  }, [clamp, save, defaultWidth]);

  return {
    gridRef,
    // Vai no `style` da grade, que usa `lg:grid-cols-[var(--list-w)_auto_1fr]`.
    gridStyle: { "--list-w": `${width}px` },
    splitterProps: { width, onPointerDown: startDrag, onKeyDown, onDoubleClick: reset },
  };
}

// O divisor entre as duas colunas; só aparece no computador.
export function Splitter({ width, label, ...handlers }) {
  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={label}
      aria-valuenow={width}
      tabIndex={0}
      title="Arraste para ajustar (duplo clique volta ao padrão)"
      {...handlers}
      className="group hidden w-4 cursor-col-resize touch-none items-center justify-center outline-none lg:flex"
    >
      <span className="h-12 w-1 rounded-full bg-line transition-colors group-hover:bg-primary group-focus-visible:bg-primary" />
    </div>
  );
}

// Classes da grade que recebe o divisor.
export const SPLIT_GRID = "lg:grid-cols-[var(--list-w)_auto_1fr] lg:gap-x-1";
