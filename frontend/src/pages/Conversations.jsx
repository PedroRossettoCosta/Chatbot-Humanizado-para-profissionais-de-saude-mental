import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api, mediaUrl } from "../api.js";
import {
  AlertIcon,
  ArrowLeftIcon,
  BotIcon,
  ChatIcon,
  HandIcon,
  HourglassIcon,
  LockIcon,
  SearchIcon,
  SendIcon,
} from "../components/icons.jsx";
import { Button, ErrorBox, Tag, dayKey, dayLabel, formatTime as time, shortWhen } from "../components/ui.jsx";
import { usePanel } from "../panel/PanelContext.jsx";

// Sem tempo real no MVP: a lista e a conversa aberta são relidas sozinhas.
const LIST_REFRESH_MS = 10000;
const CONVERSATION_REFRESH_MS = 5000;

// Pedidos que a SelenIA levou com `avisar_profissional` (o bot continua
// respondendo). Os outros motivos são a pessoa pedindo você.
const ASSISTANT_REQUESTS = {
  horario_especial: "pediu um horário fora do seu atendimento",
  pagamento: "perguntou sobre uma forma de pagamento que não está no seu perfil",
  valor: "pediu uma exceção no valor ou perguntou um valor que não está no seu perfil",
  outro: "fez uma pergunta que só você pode responder",
};

// Etiquetas de uma conversa: a situação principal primeiro.
function tagsOf(c) {
  const tags = [];
  if (c.state === "emergency_hold") tags.push({ text: "Pausada após emergência", tone: "danger" });
  if (c.awaiting_reply_since) tags.push({ text: "Aguardando você", tone: "warning" });
  if (c.needs_attention && c.state !== "emergency_hold") tags.push({ text: "Necessita atenção", tone: "warning" });
  if (c.state === "human") tags.push({ text: "Você assumiu", tone: "info" });
  if (c.state === "active" && !c.awaiting_reply_since) tags.push({ text: "SelenIA atendendo", tone: "primary" });
  if (c.channel === "simulator") tags.push({ text: "Teste", tone: "neutral" });
  return tags;
}

const needsYou = (c) => c.state === "emergency_hold" || Boolean(c.awaiting_reply_since) || c.needs_attention;

const FILTERS = [
  { key: "all", label: "Todas", test: () => true },
  { key: "you", label: "Precisam de você", test: needsYou },
  { key: "emergency", label: "Emergência", test: (c) => c.state === "emergency_hold" },
  { key: "awaiting", label: "Aguardando você", test: (c) => Boolean(c.awaiting_reply_since) },
  { key: "human", label: "Com você", test: (c) => c.state === "human" },
  { key: "bot", label: "SelenIA atendendo", test: (c) => c.state === "active" },
];

function timeLeft(iso) {
  const ms = new Date(iso).getTime() - Date.now();
  const hours = Math.floor(ms / 3600000);
  if (hours >= 1) return `${hours} h`;
  return `${Math.max(1, Math.floor(ms / 60000))} min`;
}

function preview(last) {
  if (!last) return "";
  if (last.role === "user") return `"${last.preview}"`;
  return `${last.sent_by === "professional" ? "Você" : "SelenIA"}: ${last.preview}`;
}

function Avatar({ conversation, size = "h-11 w-11" }) {
  if (conversation.channel === "simulator") {
    return (
      <span className={`flex shrink-0 items-center justify-center rounded-full bg-[#eff4ff] text-slate ${size}`}>
        <BotIcon size={20} />
      </span>
    );
  }
  const initials = conversation.contact_name.startsWith("+")
    ? "#"
    : conversation.contact_name
        .split(" ")
        .slice(0, 2)
        .map((part) => part[0])
        .join("")
        .toUpperCase();
  return (
    <span className={`flex shrink-0 items-center justify-center rounded-full bg-primary-soft font-semibold text-primary ${size}`}>
      {initials}
    </span>
  );
}

// Conversas (protótipo: conversas_inbox_maria; no celular, M1 a M3). No
// computador, lista e conversa lado a lado; no celular, uma de cada vez.
export default function Conversations() {
  const { professional, openSimulator } = usePanel();
  const { conversationId } = useParams();
  const [list, setList] = useState(null);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");

  const loadList = useCallback(() => {
    api
      .listConversations(professional.slug)
      .then((data) => {
        setList(data);
        setError("");
      })
      .catch((err) => setError(err.message));
  }, [professional.slug]);

  useEffect(() => {
    loadList();
    const id = setInterval(loadList, LIST_REFRESH_MS);
    return () => clearInterval(id);
  }, [loadList]);

  const visible = useMemo(() => {
    const test = FILTERS.find((f) => f.key === filter).test;
    const term = search.trim().toLowerCase();
    return (list || []).filter(
      (c) =>
        test(c) &&
        (!term || c.contact_name.toLowerCase().includes(term) || (c.contact_phone || "").replace(/\D/g, "").includes(term))
    );
  }, [list, filter, search]);

  return (
    <div className="mx-auto grid h-[calc(100dvh-8.5rem)] min-h-[480px] max-w-7xl gap-6 lg:grid-cols-[400px_1fr] [&>*]:min-w-0">
      {/* Lista */}
      <section className={`min-h-0 flex-col ${conversationId ? "hidden lg:flex" : "flex"}`}>
        <div className="rounded-3xl border border-line bg-white p-4">
          <label className="flex items-center gap-2 rounded-2xl bg-[#f1f5ff] px-4 py-2.5 text-muted">
            <SearchIcon size={18} />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar pelo nome ou número..."
              className="min-w-0 flex-1 border-0 bg-transparent text-[15px] text-ink outline-none"
            />
          </label>
          <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
            {FILTERS.map((f) => {
              const count = (list || []).filter(f.test).length;
              const active = filter === f.key;
              return (
                <button
                  key={f.key}
                  type="button"
                  onClick={() => setFilter(f.key)}
                  className={`shrink-0 cursor-pointer whitespace-nowrap rounded-full border-0 px-3 py-1.5 text-sm font-medium ${
                    active ? "bg-primary text-white" : "bg-[#eff4ff] text-slate hover:bg-primary-soft"
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
                <ChatIcon size={28} />
              </span>
              <p className="m-0 mt-3 font-semibold text-ink">Nenhuma conversa ainda</p>
              <p className="m-0 mt-1 text-sm text-muted">
                Quando alguém escrever para o seu WhatsApp, a conversa aparece aqui. Para ver como fica, converse com a
                SelenIA no teste.
              </p>
              <Button variant="soft" className="mt-4" onClick={openSimulator}>
                Testar a SelenIA
              </Button>
            </li>
          )}
          {list?.length > 0 && visible.length === 0 && (
            <li className="list-none px-2 py-6 text-center text-sm text-muted">Nenhuma conversa neste filtro.</li>
          )}
          {visible.map((c) => (
            <li key={c.id} className="list-none">
              <Link
                to={`/conversas/${c.id}`}
                className={`flex gap-3 rounded-3xl border-2 p-4 no-underline transition-colors ${
                  c.id === conversationId ? "border-primary" : "border-transparent hover:border-line"
                } ${c.state === "emergency_hold" ? "bg-[#fff7f7]" : "bg-white"}`}
              >
                <Avatar conversation={c} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="truncate font-semibold text-ink">{c.contact_name}</span>
                    {c.last_message_at && (
                      <span className="shrink-0 text-xs text-muted">{shortWhen(c.last_message_at)}</span>
                    )}
                  </div>
                  {c.contact_phone && c.contact_phone !== c.contact_name && (
                    <p className="m-0 text-sm text-muted">{c.contact_phone}</p>
                  )}
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {tagsOf(c).map((t) => (
                      <Tag key={t.text} tone={t.tone}>
                        {t.text}
                      </Tag>
                    ))}
                  </div>
                  <p className="m-0 mt-2 line-clamp-2 text-sm leading-snug text-slate">{preview(c.last_message)}</p>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      {/* Conversa aberta */}
      <section className={`min-h-0 ${conversationId ? "flex" : "hidden lg:flex"}`}>
        {conversationId ? (
          <ConversationView key={conversationId} conversationId={conversationId} onChanged={loadList} />
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center rounded-3xl border border-line bg-white p-8 text-center">
            <span className="text-primary">
              <ChatIcon size={32} />
            </span>
            <p className="m-0 mt-3 font-semibold text-ink">Escolha uma conversa</p>
            <p className="m-0 mt-1 max-w-sm text-sm text-muted">
              As que precisam de você aparecem primeiro: emergência, quem pediu para falar com você e o que a triagem
              marcou para atenção.
            </p>
          </div>
        )}
      </section>
    </div>
  );
}

const MEDIA_GONE = "Arquivo não disponível. O WhatsApp guarda por cerca de 30 dias.";

// Foto, áudio ou documento que a pessoa mandou, buscado na Meta só quando
// aparece na tela.
function Media({ conversationId, message }) {
  const [failed, setFailed] = useState(false);
  const src = mediaUrl(conversationId, message.id);
  if (failed) return <span className="text-sm text-muted">{message.content} · {MEDIA_GONE}</span>;
  if (message.media_type === "image") {
    return (
      <a href={src} target="_blank" rel="noreferrer" title="Abrir a foto em tamanho maior">
        <img
          src={src}
          alt="Foto enviada pela pessoa"
          loading="lazy"
          className="block max-h-80 max-w-full rounded-xl"
          onError={() => setFailed(true)}
        />
      </a>
    );
  }
  if (message.media_type === "audio") {
    return <audio controls preload="none" src={src} className="max-w-full" onError={() => setFailed(true)} />;
  }
  return (
    <a href={src} target="_blank" rel="noreferrer" className="font-semibold text-primary">
      📄 {message.media_filename || "Documento"}
    </a>
  );
}

function Bubble({ message, conversationId }) {
  const incoming = message.role === "user";
  const label = incoming
    ? null
    : message.sent_by === "professional"
      ? "Você"
      : message.sent_by === "system"
        ? "SelenIA · mensagem fixa"
        : "SelenIA";
  const style = incoming
    ? "rounded-tl-md border border-line bg-white"
    : message.sent_by === "professional"
      ? "rounded-tr-md bg-[#dfeee2]"
      : message.sent_by === "system"
        ? "rounded-tr-md border border-[#c7d6f5] bg-[#eff4ff]"
        : "rounded-tr-md bg-primary-soft";
  return (
    <div className={`flex flex-col ${incoming ? "items-start" : "items-end"}`}>
      {label && <p className="m-0 mb-1 text-xs font-semibold text-primary">{label}</p>}
      <div className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-[15px] leading-relaxed text-ink ${style}`}>
        {message.media_type ? <Media conversationId={conversationId} message={message} /> : message.content}
      </div>
      <span className="mt-1 text-xs text-muted">
        {time(message.created_at)}
        {message.delivery_failed && (
          <span className="ml-2 font-semibold text-danger" title="A Meta recusou o envio. A pessoa não recebeu esta mensagem.">
            · Não entregue
          </span>
        )}
      </span>
    </div>
  );
}

function ConversationView({ conversationId, onChanged }) {
  const { professional } = usePanel();
  const navigate = useNavigate();
  const [conversation, setConversation] = useState(null);
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirmRelease, setConfirmRelease] = useState(false);
  const [error, setError] = useState("");
  const scrollRef = useRef(null);
  const seenCount = useRef(0);

  const load = useCallback(() => {
    api
      .getConversation(conversationId)
      .then(setConversation)
      .catch((err) => {
        if (err.status === 404) navigate("/conversas", { replace: true });
        else setError(err.message);
      });
  }, [conversationId, navigate]);

  useEffect(() => {
    load();
    const id = setInterval(load, CONVERSATION_REFRESH_MS);
    return () => clearInterval(id);
  }, [load]);

  // Desce para o fim ao abrir e quando chega mensagem nova.
  useEffect(() => {
    const count = conversation?.messages.length || 0;
    if (count > seenCount.current && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
    seenCount.current = count;
  }, [conversation]);

  async function act(action) {
    setBusy(true);
    setError("");
    try {
      setConversation(await action());
      onChanged();
      return true;
    } catch (err) {
      setError(err.message);
      if (err.status === 409) load();
      return false;
    } finally {
      setBusy(false);
      setConfirmRelease(false);
    }
  }

  async function send(event) {
    event?.preventDefault();
    const text = reply.trim();
    if (!text || busy) return;
    if (await act(() => api.sendProfessionalMessage(conversationId, text))) setReply("");
  }

  if (!conversation) {
    return (
      <div className="flex flex-1 items-center justify-center rounded-3xl border border-line bg-white text-sm text-muted">
        {error || "Carregando..."}
      </div>
    );
  }

  const c = conversation;
  const isTest = c.channel === "simulator";
  let lastDay = null;

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-3xl border border-line bg-white">
      {/* Cabeçalho */}
      <header className="flex flex-wrap items-center gap-3 border-b border-line bg-[#f8faff] px-4 py-3 sm:px-5">
        <Link
          to="/conversas"
          className="-ml-1 flex rounded-xl p-1.5 text-slate no-underline hover:bg-[#eff4ff] lg:hidden"
          aria-label="Voltar para a lista"
        >
          <ArrowLeftIcon />
        </Link>
        <Avatar conversation={c} size="h-10 w-10" />
        <div className="min-w-0 flex-1">
          <p className="m-0 truncate font-semibold text-ink">{c.contact_name}</p>
          <p className="m-0 truncate text-sm text-muted">
            {isTest ? "Simulador do painel · nada vai para o WhatsApp" : `WhatsApp · ${c.contact_phone}`}
          </p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {tagsOf(c).map((t) => (
            <Tag key={t.text} tone={t.tone}>
              {t.text}
            </Tag>
          ))}
        </div>
        <div className="flex w-full justify-end gap-2 sm:w-auto">
          {c.state === "active" && (
            <Button className="flex items-center gap-2 !px-4 !py-2 text-sm" disabled={busy} onClick={() => act(() => api.takeOver(conversationId))}>
              <HandIcon size={18} /> Assumir conversa
            </Button>
          )}
          {c.state === "human" && (
            <Button variant="soft" className="!px-4 !py-2 text-sm" disabled={busy} onClick={() => act(() => api.releaseToBot(conversationId))}>
              Devolver à SelenIA
            </Button>
          )}
          {c.state === "emergency_hold" &&
            (confirmRelease ? (
              <span className="flex flex-wrap items-center justify-end gap-2 text-sm text-slate">
                A SelenIA volta a responder aqui. Liberar?
                <Button className="!px-3 !py-1.5 text-sm" disabled={busy} onClick={() => act(() => api.releaseToBot(conversationId))}>
                  Sim
                </Button>
                <Button variant="ghost" className="!px-3 !py-1.5 text-sm" onClick={() => setConfirmRelease(false)}>
                  Não
                </Button>
              </span>
            ) : (
              <Button variant="soft" className="!px-4 !py-2 text-sm" onClick={() => setConfirmRelease(true)}>
                Liberar a SelenIA
              </Button>
            ))}
        </div>
      </header>

      {/* Avisos */}
      {c.state === "emergency_hold" && (
        <div className="flex gap-3 border-b border-[#fecaca] bg-danger-soft px-5 py-3 text-sm text-danger">
          <AlertIcon size={20} className="mt-0.5 shrink-0" />
          <p className="m-0">
            <strong>Emergência{c.latest_alert ? ` às ${time(c.latest_alert.created_at)}` : ""}.</strong> A pessoa
            recebeu a mensagem fixa (SAMU 192, CVV 188) e a SelenIA está pausada nesta conversa até você liberar. Você
            pode escrever para a pessoa normalmente.
          </p>
        </div>
      )}
      {c.awaiting_reply_since && (
        <div className="flex gap-3 border-b border-[#fde68a] bg-warning-soft px-5 py-3 text-sm text-[#92400e]">
          <HandIcon size={20} className="mt-0.5 shrink-0" />
          <p className="m-0">
            <strong>Aguardando você desde {shortWhen(c.awaiting_reply_since)}.</strong>{" "}
            {ASSISTANT_REQUESTS[c.awaiting_reason] ? (
              <>
                A pessoa {ASSISTANT_REQUESTS[c.awaiting_reason]}. A SelenIA disse que ia perguntar a você e continua
                tirando as outras dúvidas; responda por aqui.
              </>
            ) : (
              <>
                A pessoa pediu para falar com você
                {c.state === "human" ? " e a SelenIA parou de responder." : "; a SelenIA avisou que você responde por aqui."}
              </>
            )}
          </p>
        </div>
      )}
      {c.needs_attention && c.state !== "emergency_hold" && (
        <div className="flex gap-3 border-b border-[#fde68a] bg-warning-soft px-5 py-3 text-sm text-[#92400e]">
          <AlertIcon size={20} className="mt-0.5 shrink-0" />
          <p className="m-0">
            A triagem marcou esta conversa para sua atenção (sofrimento intenso ou dúvida sobre segurança). A SelenIA
            continua respondendo.
          </p>
        </div>
      )}

      {/* Mensagens */}
      <div ref={scrollRef} className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-5 sm:px-6">
        {c.messages.map((m, i) => {
          const day = dayKey(new Date(m.created_at));
          const separator = day !== lastDay;
          lastDay = day;
          return (
            <div key={i}>
              {separator && (
                <p className="m-0 mb-4 text-center">
                  <span className="rounded-full bg-[#eff4ff] px-3 py-1 text-xs text-slate">{dayLabel(m.created_at)}</span>
                </p>
              )}
              <Bubble message={m} conversationId={conversationId} />
            </div>
          );
        })}
      </div>

      {/* Resposta */}
      <footer className="border-t border-line px-4 py-3 sm:px-5">
        {error && (
          <div className="mb-2">
            <ErrorBox>{error}</ErrorBox>
          </div>
        )}
        {c.reply_window_open ? (
          <form onSubmit={send}>
            <p className="m-0 mb-2 text-xs text-muted">
              {c.state === "active"
                ? "Ao enviar, você assume a conversa e a SelenIA para de responder. "
                : c.state === "human"
                  ? "Você está no comando desta conversa. "
                  : ""}
              Você pode responder por mais {timeLeft(c.reply_window_closes_at)} (janela de 24 h do WhatsApp).
              {isTest && " Conversa de teste: a resposta fica só no painel."}
            </p>
            <div className="flex items-end gap-2">
              <textarea
                value={reply}
                onChange={(e) => setReply(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    send();
                  }
                }}
                rows={2}
                maxLength={4000}
                placeholder={`Responder como ${professional.name}...`}
                className="min-w-0 flex-1 resize-none rounded-2xl border border-line bg-[#f8faff] px-4 py-3 text-[15px] outline-none focus:border-primary focus:ring-4 focus:ring-primary/15"
              />
              <Button type="submit" className="flex items-center gap-2 !px-5" disabled={busy || !reply.trim()}>
                Enviar <SendIcon size={16} />
              </Button>
            </div>
          </form>
        ) : (
          <div className="rounded-2xl border border-[#fde68a] bg-warning-soft p-4">
            <div className="flex gap-3">
              <span className="text-[#92400e]">
                <HourglassIcon size={22} />
              </span>
              <div>
                <p className="m-0 font-semibold text-[#92400e]">Janela de 24 horas encerrada</p>
                <p className="m-0 mt-1 text-sm text-[#92400e]">
                  Passaram 24 horas desde a última mensagem desta pessoa. Pelas regras do WhatsApp, você só pode
                  responder quando ela escrever de novo.
                </p>
              </div>
            </div>
            <div className="mt-3 flex items-center gap-2 rounded-xl bg-white/70 px-3 py-2 text-sm text-muted">
              <LockIcon size={16} /> Envio indisponível até a pessoa escrever
            </div>
          </div>
        )}
      </footer>
    </div>
  );
}
