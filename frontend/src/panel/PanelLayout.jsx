import { useCallback, useEffect, useMemo, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { api } from "../api.js";
import Logo from "../components/Logo.jsx";
import { nameNeedsAction } from "../components/WhatsAppConnect.jsx";
import {
  BellIcon,
  BookIcon,
  BotIcon,
  CalendarIcon,
  ChatIcon,
  MenuIcon,
  PhoneIcon,
  ProfileIcon,
  UsersIcon,
} from "../components/icons.jsx";
import InSessionControl from "./InSessionControl.jsx";
import { PanelContext } from "./PanelContext.jsx";
import Simulator from "./Simulator.jsx";

// Menu do protótipo. As telas marcadas `soon` ainda não existem: aparecem
// para mostrar a estrutura, mas não abrem (entram nos dias do plano).
const NAV = [
  { label: "Conversas", icon: ChatIcon, to: "/conversas" },
  { label: "Alertas", icon: BellIcon, to: "/alertas", badge: "alerts" },
  { label: "Agenda", icon: CalendarIcon, to: "/agenda", badge: "appointments" },
  { label: "Clientes", icon: UsersIcon, to: "/clientes" },
  { label: "Perfil do atendimento", icon: ProfileIcon, to: "/perfil" },
  { label: "WhatsApp", icon: PhoneIcon, to: "/whatsapp", badge: "whatsapp" },
  { label: "Base de conhecimento", icon: BookIcon, to: "/base-de-conhecimento" },
];

const TITLES = {
  "/conversas": "Conversas",
  "/alertas": "Alertas",
  "/agenda": "Agenda",
  "/clientes": "Clientes",
  "/perfil": "Perfil do atendimento",
  "/whatsapp": "WhatsApp",
  "/base-de-conhecimento": "Base de conhecimento",
};

// Estrutura do painel (protótipo: menu lateral + barra do topo). O
// simulador fica montado o tempo todo, só escondido: fechar e abrir não
// apaga a conversa de teste.
export default function PanelLayout({ me, onLogout, startWithSimulator }) {
  const [professional, setProfessional] = useState(me.professional);
  const [simulatorOpen, setSimulatorOpen] = useState(Boolean(startWithSimulator));
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();

  useEffect(() => setMenuOpen(false), [location.pathname]);

  // O "Em consulta" desliga sozinho no horário; relê a profissional a cada
  // minuto para o topo não mostrar um estado vencido.
  useEffect(() => {
    const id = setInterval(() => {
      api
        .getProfessional(professional.slug)
        .then(setProfessional)
        .catch(() => {});
    }, 60000);
    return () => clearInterval(id);
  }, [professional.slug]);

  // Alertas sem revisar, no número do menu. A tela de Alertas chama
  // `refreshAlertCount` quando um alerta é revisado.
  const [unreviewedAlerts, setUnreviewedAlerts] = useState(0);
  const refreshAlertCount = useCallback(() => {
    api
      .listAlerts(professional.slug)
      .then((list) => setUnreviewedAlerts(list.filter((a) => a.status === "new").length))
      .catch(() => {});
  }, [professional.slug]);
  useEffect(() => {
    refreshAlertCount();
    const id = setInterval(refreshAlertCount, 10000);
    return () => clearInterval(id);
  }, [refreshAlertCount]);

  // Pedidos de horário aguardando confirmação, no número do menu. A tela
  // Agenda chama `refreshAppointmentCount` ao confirmar ou recusar.
  const [pendingAppointments, setPendingAppointments] = useState(0);
  const refreshAppointmentCount = useCallback(() => {
    api
      .listAppointments(professional.slug)
      .then((list) => setPendingAppointments(list.filter((a) => a.awaiting_decision).length))
      .catch(() => {});
  }, [professional.slug]);
  useEffect(() => {
    refreshAppointmentCount();
    const id = setInterval(refreshAppointmentCount, 30000);
    return () => clearInterval(id);
  }, [refreshAppointmentCount]);

  // Resposta da Meta sobre o nome novo do WhatsApp (aprovado para aplicar
  // ou recusado). A consulta vai até a Meta, então é espaçada; a tela
  // WhatsApp atualiza na hora por `onWhatsAppStatus`.
  const [whatsappAction, setWhatsappAction] = useState(false);
  const onWhatsAppStatus = useCallback((status) => setWhatsappAction(nameNeedsAction(status)), []);
  useEffect(() => {
    const refresh = () =>
      api
        .getWhatsApp(professional.slug)
        .then(onWhatsAppStatus)
        .catch(() => {});
    refresh();
    const id = setInterval(refresh, 5 * 60000);
    return () => clearInterval(id);
  }, [professional.slug, onWhatsAppStatus]);

  const openSimulator = useCallback(() => setSimulatorOpen(true), []);
  const context = useMemo(
    () => ({
      me,
      professional,
      setProfessional,
      openSimulator,
      logout: onLogout,
      refreshAlertCount,
      refreshAppointmentCount,
      onWhatsAppStatus,
    }),
    [me, professional, openSimulator, onLogout, refreshAlertCount, refreshAppointmentCount, onWhatsAppStatus]
  );

  const sidebar = (
    <aside className="flex h-full w-72 flex-col border-r border-line bg-white px-4 py-6">
      <Logo className="px-2" />
      <p className="mt-8 mb-2 px-3 text-xs font-semibold tracking-wider text-muted">NAVEGAÇÃO</p>
      <nav className="flex flex-col gap-1">
        {NAV.map(({ label, icon: Icon, to, soon, badge }) =>
          soon ? (
            <span
              key={label}
              className="flex items-center gap-3 rounded-2xl px-3 py-2.5 text-[15px] text-muted/70"
              title="Chega nos próximos dias"
            >
              <Icon />
              <span className="flex-1">{label}</span>
              <span className="rounded-full bg-[#eff4ff] px-2 py-0.5 text-[10px] font-semibold tracking-wide">
                EM BREVE
              </span>
            </span>
          ) : (
            <NavLink
              key={label}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-2xl px-3 py-2.5 text-[15px] no-underline ${
                  isActive ? "bg-primary text-white" : "text-slate hover:bg-primary-soft"
                }`
              }
            >
              <Icon />
              <span className="flex-1">{label}</span>
              {badge === "appointments" && pendingAppointments > 0 && (
                <span
                  className="min-w-6 rounded-full bg-warning-soft px-1.5 py-0.5 text-center text-xs font-bold text-[#92400e]"
                  title="Horários aguardando sua confirmação"
                >
                  {pendingAppointments}
                </span>
              )}
              {badge === "whatsapp" && whatsappAction && (
                <span
                  className="min-w-6 rounded-full bg-danger px-1.5 py-0.5 text-center text-xs font-bold text-white"
                  title="O WhatsApp respondeu sobre o nome novo"
                >
                  1
                </span>
              )}
              {badge === "alerts" && unreviewedAlerts > 0 && (
                <span
                  className="min-w-6 rounded-full bg-danger px-1.5 py-0.5 text-center text-xs font-bold text-white"
                  title="Alertas sem revisar"
                >
                  {unreviewedAlerts}
                </span>
              )}
            </NavLink>
          )
        )}
        <button
          type="button"
          onClick={openSimulator}
          className="flex cursor-pointer items-center gap-3 rounded-2xl border-0 bg-transparent px-3 py-2.5 text-left text-[15px] text-slate hover:bg-primary-soft"
        >
          <BotIcon />
          Testar o chat
        </button>
      </nav>

      <div className="mt-auto rounded-2xl bg-[#eff4ff] p-4">
        <p className="m-0 text-sm font-semibold text-ink">Testar a SelenIA</p>
        <p className="m-0 mt-1 text-sm text-muted">Converse como se fosse uma pessoa procurando atendimento.</p>
        <button
          type="button"
          onClick={openSimulator}
          className="mt-2 cursor-pointer border-0 bg-transparent p-0 text-sm font-semibold text-primary hover:underline"
        >
          Simular fluxo →
        </button>
      </div>
      <p className="m-0 mt-4 px-2 text-xs text-muted">© SelenIA</p>
    </aside>
  );

  return (
    <PanelContext.Provider value={context}>
      <div className="flex min-h-screen">
        <div className="sticky top-0 hidden h-screen lg:block">{sidebar}</div>

        {menuOpen && (
          <div className="fixed inset-0 z-40 lg:hidden">
            <div className="absolute inset-0 bg-ink/30" onClick={() => setMenuOpen(false)} />
            <div className="relative h-full w-72">{sidebar}</div>
          </div>
        )}

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-20 flex flex-wrap items-center gap-3 border-b border-line bg-white/90 px-4 py-3 backdrop-blur sm:px-8">
            <button
              type="button"
              onClick={() => setMenuOpen(true)}
              className="cursor-pointer rounded-xl border-0 bg-transparent p-2 text-slate lg:hidden"
              aria-label="Abrir menu"
            >
              <MenuIcon />
            </button>
            <p className="m-0 flex-1 text-sm text-muted">
              Painel <span className="mx-1">›</span>
              <span className="font-semibold text-primary">{TITLES[location.pathname] || TITLES["/" + location.pathname.split("/")[1]] || ""}</span>
            </p>
            <InSessionControl />
            <div className="flex items-center gap-3 border-l border-line pl-3">
              <div className="hidden text-right sm:block">
                <p className="m-0 text-sm font-semibold text-ink">{professional.name}</p>
                <p className="m-0 text-xs text-muted">{me.email}</p>
              </div>
              {me.picture_url ? (
                <img src={me.picture_url} alt="" className="h-9 w-9 rounded-full" referrerPolicy="no-referrer" />
              ) : (
                <span className="flex h-9 w-9 items-center justify-center rounded-full bg-primary-soft font-semibold text-primary">
                  {professional.name.slice(0, 1)}
                </span>
              )}
              <button
                type="button"
                onClick={onLogout}
                className="cursor-pointer border-0 bg-transparent p-0 text-sm text-muted hover:text-ink"
              >
                Sair
              </button>
            </div>
          </header>

          <main className="flex-1 px-4 py-8 sm:px-8">
            <Outlet />
          </main>
        </div>
      </div>

      <Simulator open={simulatorOpen} onClose={() => setSimulatorOpen(false)} />
    </PanelContext.Provider>
  );
}
