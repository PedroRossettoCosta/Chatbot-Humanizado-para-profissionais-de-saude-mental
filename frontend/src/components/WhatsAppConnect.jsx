// Conectar o número de WhatsApp da profissional (etapa 6 do cadastro e
// tela WhatsApp do menu). Os passos são os da Meta: cadastrar o número, receber o
// código por SMS ou ligação, confirmar o código e registrar. O backend
// faz as chamadas (`services/whatsapp_numbers.py`); aqui só a conversa
// com a profissional. Depois de conectado, dá para trocar o nome que
// aparece ou desconectar o número para pôr outro.

import { useEffect, useState } from "react";

import { api } from "../api.js";
import { Button, ErrorBox, Field, Tag, inputClass } from "./ui.jsx";

// Como a Meta chama o estado do nome que aparece no WhatsApp.
const NAME_STATUS = {
  APPROVED: ["primary", "Nome aprovado"],
  AVAILABLE_WITHOUT_REVIEW: ["primary", "Nome liberado"],
  PENDING_REVIEW: ["warning", "Nome em análise"],
  DECLINED: ["danger", "Nome recusado"],
};

// Resposta da Meta sobre o nome novo que ainda pede atenção: aprovado e
// não aplicado, ou recusado e ainda não visto nesta tela. Acende a bolinha
// vermelha do item WhatsApp do menu.
const DECLINED_SEEN_KEY = "selenia-whatsapp-recusa-vista";

function declinedSeen(name) {
  try {
    return localStorage.getItem(DECLINED_SEEN_KEY) === name;
  } catch {
    return false;
  }
}

export function nameNeedsAction(status) {
  if (!status?.connected) return false;
  if (status.new_name_status === "APPROVED") return status.new_display_name !== status.verified_name;
  if (status.new_name_status === "DECLINED") return !declinedSeen(status.new_display_name);
  return false;
}

function BrazilPrefix() {
  // Bandeira desenhada: o Windows não mostra emoji de bandeira (aparece "BR").
  return (
    <span className="flex shrink-0 items-center gap-2 whitespace-nowrap bg-[#eff4ff] px-4 text-slate">
      <svg width="22" height="16" viewBox="0 0 22 16" aria-hidden="true" className="rounded-sm">
        <rect width="22" height="16" fill="#009c3b" />
        <path d="M11 2 L20 8 L11 14 L2 8 Z" fill="#ffdf00" />
        <circle cx="11" cy="8" r="3.4" fill="#002776" />
      </svg>
      +55
    </span>
  );
}

export default function WhatsAppConnect({ slug, defaultName, onStatus }) {
  const [status, setStatus] = useState(null);
  const [number, setNumber] = useState("");
  const [displayName, setDisplayName] = useState(defaultName || "");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [renaming, setRenaming] = useState(false);
  const [newName, setNewName] = useState("");

  function update(next) {
    // Abrir a tela já conta como ver a recusa do nome.
    if (next?.connected && next.new_name_status === "DECLINED") {
      try {
        localStorage.setItem(DECLINED_SEEN_KEY, next.new_display_name || "");
      } catch {
        // Sem armazenamento: a bolinha volta na próxima consulta, sem problema.
      }
    }
    setStatus(next);
    onStatus?.(next);
  }

  useEffect(() => {
    api
      .getWhatsApp(slug)
      .then(update)
      .catch((e) => setError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug]);

  async function run(action, successNotice = "") {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      update(await action());
      setNotice(successNotice);
    } catch (e) {
      setError(e.message);
      // O passo pode ter andado mesmo com erro (ex.: código certo, registro recusado).
      api.getWhatsApp(slug).then(update).catch(() => {});
    } finally {
      setBusy(false);
    }
  }

  if (!status) {
    return error ? <ErrorBox>{error}</ErrorBox> : <p className="text-muted">Carregando...</p>;
  }

  if (status.connected) {
    const name = NAME_STATUS[status.name_status];
    return (
      <div className="rounded-2xl border border-primary/30 bg-primary-soft px-5 py-4">
        <p className="m-0 font-semibold text-primary">✓ WhatsApp conectado</p>
        <p className="m-0 mt-1 text-lg text-ink">{status.display_number || "Número conectado"}</p>
        {status.verified_name && <p className="m-0 text-sm text-slate">Aparece como “{status.verified_name}”</p>}
        <div className="mt-3 flex flex-wrap gap-2">
          {status.meta_status && (
            <Tag tone={status.meta_status === "CONNECTED" ? "primary" : "warning"}>
              {status.meta_status === "CONNECTED" ? "Recebendo mensagens" : `Meta: ${status.meta_status}`}
            </Tag>
          )}
          {name && <Tag tone={name[0]}>{name[1]}</Tag>}
        </div>
        {status.name_status === "PENDING_REVIEW" && (
          <p className="m-0 mt-3 text-sm text-slate">
            O WhatsApp ainda está analisando o nome. Enquanto isso, as pessoas veem só o número.
          </p>
        )}

        {status.new_name_status === "PENDING" && (
          <p className="m-0 mt-3 text-sm text-slate">
            Nome novo “{status.new_display_name}” em análise pelo WhatsApp (costuma levar de 1 a 2 dias). Até lá, continua
            o nome atual.
          </p>
        )}
        {status.new_name_status === "APPROVED" && status.new_display_name !== status.verified_name && (
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <p className="m-0 text-sm text-slate">
              O WhatsApp aprovou o nome novo “{status.new_display_name}”. Falta aplicar para ele aparecer.
            </p>
            <Button
              className="px-4 py-2 text-sm"
              disabled={busy}
              onClick={() => run(() => api.applyWhatsAppName(slug), "Nome novo aplicado.")}
            >
              {busy ? "Aplicando..." : "Aplicar nome novo"}
            </Button>
          </div>
        )}
        {status.new_name_status === "DECLINED" && !renaming && (
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <p className="m-0 text-sm text-danger">
              O WhatsApp recusou o nome “{status.new_display_name}”. Continua o nome atual; você pode pedir outro.
            </p>
            <Button
              variant="soft"
              className="px-4 py-2 text-sm"
              disabled={busy}
              onClick={() => {
                setNewName("");
                setRenaming(true);
              }}
            >
              Pedir outro nome
            </Button>
          </div>
        )}

        {renaming ? (
          <div className="mt-4 space-y-3">
            <Field label="Nome novo no WhatsApp" hint="Passa pela análise do WhatsApp antes de aparecer para as pessoas.">
              <input
                className={inputClass}
                value={newName}
                maxLength={100}
                onChange={(e) => setNewName(e.target.value)}
                placeholder={status.verified_name || ""}
              />
            </Field>
            <div className="flex flex-wrap gap-3">
              <Button
                className="px-4 py-2 text-sm"
                disabled={busy || newName.trim().length < 3}
                onClick={async () => {
                  await run(() => api.renameWhatsApp(slug, newName.trim()), "Nome enviado para análise do WhatsApp.");
                  setRenaming(false);
                }}
              >
                {busy ? "Enviando..." : "Enviar para análise"}
              </Button>
              <Button variant="ghost" className="px-4 py-2 text-sm" disabled={busy} onClick={() => setRenaming(false)}>
                Cancelar
              </Button>
            </div>
          </div>
        ) : (
          <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-sm">
            <button
              type="button"
              className="cursor-pointer border-0 bg-transparent p-0 text-primary underline disabled:opacity-50"
              disabled={busy}
              onClick={() => {
                setNewName(status.verified_name || "");
                setRenaming(true);
              }}
            >
              Trocar o nome
            </button>
            <button
              type="button"
              className="cursor-pointer border-0 bg-transparent p-0 text-muted underline disabled:opacity-50"
              disabled={busy}
              onClick={() => {
                if (
                  window.confirm(
                    `Desconectar ${status.display_number || "este número"}? A SelenIA para de responder por ele na hora. ` +
                      "As conversas antigas continuam no painel. Para cadastrar outro número, pode ser preciso apagar " +
                      "este no WhatsApp Manager da Meta."
                  )
                )
                  run(() => api.disconnectWhatsApp(slug), "Número desconectado. Agora você pode conectar outro.");
              }}
            >
              Trocar o número
            </button>
          </div>
        )}
        {notice && <p className="m-0 mt-3 text-sm text-primary">{notice}</p>}
        {error && (
          <div className="mt-3">
            <ErrorBox>{error}</ErrorBox>
          </div>
        )}
      </div>
    );
  }

  if (!status.configured) {
    return (
      <p className="rounded-2xl bg-[#eff4ff] px-4 py-3 text-sm text-slate">
        A conexão com o WhatsApp ainda não está configurada neste servidor. Dá para seguir e conectar depois, pelo
        item WhatsApp do menu.
      </p>
    );
  }

  if (status.step === "code_sent") {
    return (
      <div className="space-y-5">
        <p className="m-0 text-slate">
          Enviamos um código para <strong>{status.display_number}</strong>. Ele chega por SMS (ou ligação, se você
          pediu) no chip desse número.
        </p>
        <Field label="Código de 6 números" required>
          <input
            className={`${inputClass} tracking-[0.4em]`}
            value={code}
            onChange={(e) => setCode(e.target.value)}
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={7}
            placeholder="000000"
          />
        </Field>
        <Button
          className="w-full"
          disabled={busy || code.replace(/\D/g, "").length !== 6}
          onClick={() => run(() => api.verifyWhatsApp(slug, code))}
        >
          {busy ? "Conferindo..." : "Confirmar código"}
        </Button>
        <div className="flex flex-wrap justify-center gap-4 text-sm">
          <button
            type="button"
            className="cursor-pointer border-0 bg-transparent p-0 text-primary underline disabled:opacity-50"
            disabled={busy}
            onClick={() => run(() => api.resendWhatsAppCode(slug, "SMS"), "Código reenviado por SMS.")}
          >
            Reenviar por SMS
          </button>
          <button
            type="button"
            className="cursor-pointer border-0 bg-transparent p-0 text-primary underline disabled:opacity-50"
            disabled={busy}
            onClick={() => run(() => api.resendWhatsAppCode(slug, "VOICE"), "Você vai receber uma ligação com o código.")}
          >
            Receber por ligação
          </button>
          <button
            type="button"
            className="cursor-pointer border-0 bg-transparent p-0 text-muted underline disabled:opacity-50"
            disabled={busy}
            onClick={() => run(() => api.cancelWhatsApp(slug))}
          >
            Trocar o número
          </button>
        </div>
        {notice && <p className="m-0 text-center text-sm text-primary">{notice}</p>}
        <ErrorBox>{error}</ErrorBox>
      </div>
    );
  }

  if (status.step === "verified") {
    return (
      <div className="space-y-5">
        <p className="m-0 text-slate">
          O número <strong>{status.display_number}</strong> foi verificado. Falta registrar na plataforma do WhatsApp
          para ele começar a receber mensagens.
        </p>
        <Button className="w-full" disabled={busy} onClick={() => run(() => api.registerWhatsApp(slug))}>
          {busy ? "Registrando..." : "Registrar número"}
        </Button>
        <p className="m-0 text-center text-sm text-muted">
          Tentativas de registro nas últimas 72 horas: {status.registrations_last_72h} de {status.register_limit}
        </p>
        <div className="text-center text-sm">
          <button
            type="button"
            className="cursor-pointer border-0 bg-transparent p-0 text-muted underline disabled:opacity-50"
            disabled={busy}
            onClick={() => run(() => api.cancelWhatsApp(slug))}
          >
            Trocar o número
          </button>
        </div>
        <ErrorBox>{error}</ErrorBox>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex gap-3 rounded-2xl border border-warning/30 bg-warning-soft px-5 py-4">
        <span aria-hidden="true">⚠️</span>
        <div className="text-sm leading-relaxed text-[#92400e]">
          <p className="m-0 font-semibold">Atenção antes de conectar</p>
          <p className="m-0 mt-1">
            O número conectado fica exclusivo da SelenIA e deixa de funcionar no aplicativo do WhatsApp e no WhatsApp
            Web. Você responde às pessoas pelo painel. Se quiser usar o número que já atende, apague a conta do
            WhatsApp dele no celular antes; as conversas antigas não são trazidas.
          </p>
        </div>
      </div>
      <Field label="Número de WhatsApp" required hint="O chip precisa estar com você: o código chega nele.">
        <div className="mt-2 flex overflow-hidden rounded-2xl border border-line bg-white focus-within:border-primary">
          <BrazilPrefix />
          <input
            className="w-full border-0 px-4 py-3 text-base outline-none"
            value={number}
            onChange={(e) => setNumber(e.target.value)}
            placeholder="(11) 98452-7810"
            inputMode="tel"
          />
        </div>
      </Field>
      <Field
        label="Nome que aparece no WhatsApp"
        required
        hint="Este nome passa por uma análise do WhatsApp antes de aparecer para as pessoas."
      >
        <input className={inputClass} value={displayName} onChange={(e) => setDisplayName(e.target.value)} maxLength={100} />
      </Field>
      <div className="flex flex-col gap-3 sm:flex-row">
        <Button
          className="flex-1"
          disabled={busy || !number.trim() || displayName.trim().length < 3}
          onClick={() => run(() => api.startWhatsApp(slug, number, displayName, "SMS"))}
        >
          {busy ? "Enviando..." : "Enviar código por SMS"}
        </Button>
        <Button
          variant="soft"
          disabled={busy || !number.trim() || displayName.trim().length < 3}
          onClick={() => run(() => api.startWhatsApp(slug, number, displayName, "VOICE"))}
        >
          Receber por ligação
        </Button>
      </div>
      <ErrorBox>{error}</ErrorBox>
    </div>
  );
}
