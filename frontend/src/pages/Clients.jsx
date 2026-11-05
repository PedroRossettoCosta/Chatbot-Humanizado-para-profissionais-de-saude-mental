import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api.js";
import { DAYS } from "../components/WeeklyHours.jsx";
import { Button, ErrorBox, Tag, formatDateTime, shortWhen } from "../components/ui.jsx";
import { usePanel } from "../panel/PanelContext.jsx";

const TABS = [
  { key: "active", label: "Clientes ativos", test: (c) => Boolean(c.active_since) },
  { key: "others", label: "Outros contatos", test: (c) => !c.active_since },
];

function ClientRow({ client, busy, onChange }) {
  const active = Boolean(client.active_since);
  return (
    <li className="list-none rounded-3xl border border-line bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start gap-x-4 gap-y-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="m-0 font-semibold text-ink">{client.contact_name}</p>
            {client.channel === "simulator" && <Tag>Teste</Tag>}
            {client.allow_special_hours && <Tag tone="info">Especial</Tag>}
          </div>
          <p className="m-0 mt-1 text-sm text-muted">
            {[
              client.contact_phone,
              active ? `Cliente desde ${formatDateTime(client.active_since).slice(0, 10)}` : null,
              client.last_message_at ? `Última mensagem: ${shortWhen(client.last_message_at)}` : null,
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
          {client.next_session && (
            <p className="m-0 mt-1 text-sm text-slate">Próxima sessão: {client.next_session}</p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {client.conversation_id && (
            <Link
              to={`/conversas/${client.conversation_id}`}
              className="rounded-2xl px-4 py-2 text-sm font-semibold text-primary no-underline hover:bg-primary-soft"
            >
              Ver conversa
            </Link>
          )}
          {active ? (
            <Button
              variant="ghost"
              className="px-4 py-2 text-sm"
              disabled={busy}
              onClick={() => {
                if (
                  window.confirm(
                    `Tirar ${client.contact_name} da lista de clientes ativos? A condição especial e os dias dela também são apagados.`
                  )
                )
                  onChange(client, { active: false });
              }}
            >
              Tirar da lista
            </Button>
          ) : (
            <Button variant="soft" className="px-4 py-2 text-sm" disabled={busy} onClick={() => onChange(client, { active: true })}>
              Marcar como ativo
            </Button>
          )}
        </div>
      </div>
      {active && (
        <div className="mt-4 rounded-2xl bg-[#eff4ff] px-4 py-3">
          <label className="flex cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              className="mt-0.5 h-5 w-5 cursor-pointer accent-[var(--color-primary)]"
              checked={client.allow_special_hours}
              disabled={busy}
              onChange={(e) => onChange(client, { allow_special_hours: e.target.checked })}
            />
            <span>
              <span className="block font-semibold text-slate">Cliente especial</span>
              <span className="block text-sm text-muted">
                O limite de sessões por dia não vale para esta pessoa. Nos dias marcados abaixo, a SelenIA oferece a ela
                qualquer horário livre do dia, até fora do seu expediente, sem antecedência mínima.
              </span>
            </span>
          </label>
          {client.allow_special_hours && (
            <div className="mt-3 pl-8">
              <p className="m-0 text-sm font-semibold text-slate">Dias especiais desta pessoa</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {DAYS.map((d) => {
                  const on = client.special_days.includes(d.key);
                  return (
                    <button
                      key={d.key}
                      type="button"
                      aria-pressed={on}
                      disabled={busy}
                      onClick={() =>
                        onChange(client, {
                          special_days: DAYS.map((x) => x.key).filter((k) =>
                            k === d.key ? !on : client.special_days.includes(k)
                          ),
                        })
                      }
                      className={`cursor-pointer rounded-full border px-3 py-1.5 text-sm ${
                        on ? "border-primary bg-primary text-white" : "border-line bg-white text-slate hover:bg-primary-soft"
                      }`}
                    >
                      {d.label}
                    </button>
                  );
                })}
              </div>
              {client.special_days.length === 0 && (
                <p className="m-0 mt-2 text-sm text-muted">
                  Nenhum dia marcado: por enquanto vale só o fim do limite de sessões por dia.
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </li>
  );
}

// Clientes ativos e permissões (pedido do Pedro em 19/10/2026). Quem
// tem sessão confirmada entra aqui sozinho; a profissional também marca
// ou tira na mão, e escolhe os dias especiais de cada cliente especial.
export default function Clients() {
  const { professional } = usePanel();
  const [clients, setClients] = useState(null);
  const [tab, setTab] = useState("active");
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState("");

  const slug = professional.slug;

  const load = useCallback(
    () =>
      api
        .listClients(slug)
        .then(setClients)
        .catch((err) => setError(err.message)),
    [slug]
  );

  useEffect(() => {
    load();
  }, [load]);

  async function change(client, payload) {
    setBusyId(client.id);
    setError("");
    try {
      const updated = await api.updateClient(client.id, payload);
      setClients((list) => list.map((c) => (c.id === updated.id ? updated : c)));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  const visible = (clients || []).filter(TABS.find((t) => t.key === tab).test);

  return (
    <div className="mx-auto max-w-6xl pb-12">
      <p className="m-0 text-xs font-semibold tracking-wider text-primary">QUEM VOCÊ ATENDE</p>
      <h1 className="m-0 mt-2 text-4xl font-bold tracking-tight text-ink">Clientes</h1>
      <p className="m-0 mt-2 max-w-2xl text-muted">
        Quem tem sessão confirmada entra na lista sozinho. Aqui você tira ou acrescenta clientes e dá condição especial
        a quem precisa: os dias em que a pessoa pode marcar a qualquer hora, sem o limite de sessões por dia.
      </p>

      {error && (
        <div className="mt-6">
          <ErrorBox>{error}</ErrorBox>
        </div>
      )}

      <div className="mt-6 max-w-4xl">
        <section>
          <div className="flex flex-wrap items-center gap-2">
            {TABS.map((t) => (
              <button
                key={t.key}
                type="button"
                onClick={() => setTab(t.key)}
                className={`cursor-pointer whitespace-nowrap rounded-full border-0 px-4 py-2 text-sm ${
                  tab === t.key ? "bg-primary text-white" : "bg-[#eff4ff] text-slate hover:bg-primary-soft"
                }`}
              >
                {t.label} ({(clients || []).filter(t.test).length})
              </button>
            ))}
          </div>
          <ul className="m-0 mt-4 space-y-4 p-0">
            {!clients && <li className="list-none text-sm text-muted">Carregando...</li>}
            {clients && visible.length === 0 && (
              <li className="list-none rounded-3xl border border-dashed border-line px-5 py-6 text-sm text-muted">
                {tab === "active"
                  ? "Nenhum cliente ativo ainda. Quando você confirmar uma sessão pedida na conversa, a pessoa aparece aqui."
                  : "Nenhum outro contato."}
              </li>
            )}
            {visible.map((c) => (
              <ClientRow key={c.id} client={c} busy={busyId === c.id} onChange={change} />
            ))}
          </ul>
        </section>

      </div>
    </div>
  );
}
