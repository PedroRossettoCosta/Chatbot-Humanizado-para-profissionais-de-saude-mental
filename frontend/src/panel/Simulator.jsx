import { useEffect, useRef, useState } from "react";

import { api } from "../api.js";
import { BotIcon, CloseIcon, RefreshIcon, SendIcon } from "../components/icons.jsx";
import { usePanel } from "./PanelContext.jsx";

// Etiquetas de "o que aconteceu" embaixo de cada resposta (protótipo:
// simulador_testar_a_maria).
const TRIAGE_TAGS = {
  normal: { text: "Triagem: normal", tone: "neutral" },
  intense_suffering: { text: "Triagem: sofrimento intenso · necessita atenção", tone: "warning" },
  possible_risk: { text: "Triagem: dúvida sobre segurança", tone: "warning" },
  emergency: { text: "Triagem: emergência", tone: "danger" },
};
const HANDOFF_TAGS = {
  wants_professional: "Pediu para falar com você",
  bot_refused: "Recusou falar com a assistente",
};
const TONES = {
  neutral: "bg-[#eff4ff] text-slate",
  warning: "bg-warning-soft text-[#92400e]",
  danger: "bg-danger-soft text-danger",
  primary: "bg-primary-soft text-primary",
};

function Tag({ tone = "neutral", children }) {
  return <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${TONES[tone]}`}>{children}</span>;
}

function tagsFor(response) {
  const tags = [TRIAGE_TAGS[response.triage_level] || TRIAGE_TAGS.normal];
  if (response.handoff) tags.push({ text: HANDOFF_TAGS[response.handoff], tone: "warning" });
  if (response.alert_created) tags.push({ text: "Alerta criado · aviso por e-mail", tone: "danger" });
  if (response.state === "emergency_hold") tags.push({ text: "SelenIA pausada nesta conversa", tone: "danger" });
  else if (response.state === "human") tags.push({ text: "Conversa passou para você", tone: "warning" });
  for (const source of response.sources || []) tags.push({ text: `Com base em: ${source}`, tone: "primary" });
  return tags;
}

// "Testar a SelenIA": conversa de teste no mesmo caminho do WhatsApp
// (triagem, alerta, handoff, RAG), sem sair do painel. Nada é enviado
// ao WhatsApp. Também dá para testar assumir, responder e devolver.
export default function Simulator({ open, onClose }) {
  const { professional } = usePanel();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [reply, setReply] = useState("");
  const [sessionId, setSessionId] = useState(null);
  const [conversationId, setConversationId] = useState(null);
  const [state, setState] = useState("active");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, open]);

  function reset() {
    setMessages([]);
    setSessionId(null);
    setConversationId(null);
    setState("active");
    setError("");
  }

  async function send(event) {
    event.preventDefault();
    const text = input.trim();
    if (!text) return;
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setSending(true);
    setError("");
    try {
      const response = await api.sendChatMessage(professional.slug, text, sessionId);
      setSessionId(response.session_id);
      setConversationId(response.conversation_id);
      setState(response.state);
      setMessages((prev) => {
        const next = [...prev];
        if (response.disclaimer) next.push({ role: "disclaimer", content: response.disclaimer });
        next.push(
          response.reply
            ? { role: "assistant", content: response.reply, tags: tagsFor(response), fixed: response.triage_level === "emergency" }
            : { role: "silent", tags: tagsFor(response) }
        );
        return next;
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  }

  async function conversationAction(action) {
    setError("");
    try {
      const conversation = await action();
      setState(conversation.state);
    } catch (err) {
      setError(err.message);
    }
  }

  async function sendAsProfessional(event) {
    event.preventDefault();
    const text = reply.trim();
    if (!text) return;
    await conversationAction(() => api.sendProfessionalMessage(conversationId, text));
    setMessages((prev) => [...prev, { role: "professional", content: text }]);
    setReply("");
  }

  return (
    <div className={`fixed inset-0 z-50 ${open ? "" : "pointer-events-none"}`} aria-hidden={!open}>
      <div
        className={`absolute inset-0 bg-ink/25 transition-opacity ${open ? "opacity-100" : "opacity-0"}`}
        onClick={onClose}
      />
      <section
        className={`absolute right-0 top-0 flex h-full w-full max-w-xl flex-col bg-white shadow-2xl transition-transform duration-300 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
        aria-label="Testar a SelenIA"
      >
        <header className="border-b border-line px-5 py-4">
          <div className="flex items-start gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary-soft text-primary">
              <BotIcon />
            </span>
            <div className="flex-1">
              <h2 className="m-0 text-lg font-semibold text-ink">Testar a SelenIA</h2>
              <p className="m-0 text-sm text-muted">Converse como se fosse uma pessoa procurando atendimento.</p>
            </div>
            <button
              type="button"
              onClick={reset}
              className="flex cursor-pointer items-center gap-1 rounded-xl border-0 bg-[#eff4ff] px-3 py-2 text-sm text-primary hover:bg-[#dce9ff]"
            >
              <RefreshIcon size={16} /> Nova conversa
            </button>
            <button
              type="button"
              onClick={onClose}
              className="cursor-pointer rounded-xl border-0 bg-transparent p-2 text-muted hover:bg-canvas"
              aria-label="Fechar"
            >
              <CloseIcon />
            </button>
          </div>
          <p className="m-0 mt-3 rounded-xl bg-primary-soft px-3 py-2 text-xs text-primary">
            Simulação: nada aqui é enviado ao WhatsApp. Alertas e e-mails de teste acontecem de verdade.
          </p>
        </header>

        <div className="flex-1 space-y-4 overflow-y-auto bg-canvas px-5 py-5">
          {messages.length === 0 && (
            <p className="mt-10 text-center text-sm text-muted">
              Mande um “oi” para começar. A primeira resposta traz o aviso de que a SelenIA é uma inteligência artificial.
            </p>
          )}
          {messages.map((m, i) => (
            <div key={i}>
              {m.role === "user" && (
                <div className="ml-auto max-w-[85%] rounded-2xl rounded-tr-md bg-[#dce9ff] px-4 py-2.5 text-[15px] text-ink">
                  {m.content}
                </div>
              )}
              {m.role === "disclaimer" && (
                <div className="max-w-[85%] rounded-2xl border border-warning/30 bg-warning-soft px-4 py-2.5 text-sm italic text-[#92400e]">
                  {m.content}
                </div>
              )}
              {m.role === "assistant" && (
                <div className="max-w-[90%]">
                  <div
                    className={`whitespace-pre-line rounded-2xl rounded-tl-md border-l-2 px-4 py-2.5 text-[15px] text-ink ${
                      m.fixed ? "border-danger bg-white" : "border-primary bg-primary-soft"
                    }`}
                  >
                    {m.fixed && (
                      <p className="m-0 mb-1 text-xs font-semibold tracking-wide text-danger">MENSAGEM FIXA DE SEGURANÇA</p>
                    )}
                    {m.content}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {m.tags.map((t) => (
                      <Tag key={t.text} tone={t.tone}>
                        {t.text}
                      </Tag>
                    ))}
                  </div>
                </div>
              )}
              {m.role === "silent" && (
                <div>
                  <p className="m-0 text-center text-xs text-muted">
                    A SelenIA não respondeu: a conversa está com você ou pausada depois de uma emergência.
                  </p>
                  <div className="mt-2 flex flex-wrap justify-center gap-1.5">
                    {m.tags.map((t) => (
                      <Tag key={t.text} tone={t.tone}>
                        {t.text}
                      </Tag>
                    ))}
                  </div>
                </div>
              )}
              {m.role === "professional" && (
                <div className="max-w-[85%]">
                  <p className="m-0 mb-1 text-xs font-semibold text-primary">Você (pelo painel)</p>
                  <div className="rounded-2xl rounded-tl-md bg-[#e3f4e4] px-4 py-2.5 text-[15px] text-ink">{m.content}</div>
                </div>
              )}
            </div>
          ))}
          {sending && <p className="m-0 text-sm text-muted">A SelenIA está escrevendo...</p>}
          <div ref={endRef} />
        </div>

        <footer className="border-t border-line px-5 py-4">
          {conversationId && (
            <div className="mb-3 rounded-2xl bg-[#eff4ff] px-4 py-3 text-sm">
              {state === "active" ? (
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-muted">A SelenIA está respondendo.</span>
                  <button
                    type="button"
                    onClick={() => conversationAction(() => api.takeOver(conversationId))}
                    className="cursor-pointer border-0 bg-transparent p-0 font-semibold text-primary hover:underline"
                  >
                    Assumir esta conversa
                  </button>
                </div>
              ) : (
                <form onSubmit={sendAsProfessional} className="space-y-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-semibold text-slate">
                      {state === "emergency_hold" ? "Pausada após emergência" : "A conversa está com você"}
                    </span>
                    <button
                      type="button"
                      onClick={() => conversationAction(() => api.releaseToBot(conversationId))}
                      className="cursor-pointer border-0 bg-transparent p-0 font-semibold text-primary hover:underline"
                    >
                      {state === "emergency_hold" ? "Liberar SelenIA para responder" : "Devolver para a SelenIA"}
                    </button>
                  </div>
                  <div className="flex gap-2">
                    <input
                      value={reply}
                      onChange={(e) => setReply(e.target.value)}
                      placeholder={`Responder como ${professional.name}...`}
                      className="flex-1 rounded-xl border border-line bg-white px-3 py-2 outline-none focus:border-primary"
                    />
                    <button
                      type="submit"
                      disabled={!reply.trim()}
                      className="cursor-pointer rounded-xl border-0 bg-primary-soft px-3 text-sm font-semibold text-primary disabled:opacity-50"
                    >
                      Enviar
                    </button>
                  </div>
                </form>
              )}
            </div>
          )}
          {error && <p className="m-0 mb-2 text-sm text-danger">{error}</p>}
          <form onSubmit={send} className="flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Escreva como se fosse uma pessoa procurando atendimento..."
              className="flex-1 rounded-2xl border border-line bg-[#f8f9ff] px-4 py-3 outline-none focus:border-primary focus:ring-4 focus:ring-primary/15"
            />
            <button
              type="submit"
              disabled={sending || !input.trim()}
              className="flex cursor-pointer items-center gap-2 rounded-2xl border-0 bg-primary px-5 font-semibold text-white hover:bg-primary-dark disabled:opacity-50"
            >
              Enviar <SendIcon size={16} />
            </button>
          </form>
        </footer>
      </section>
    </div>
  );
}
