import { useCallback, useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { api, setSessionLostHandler } from "./api.js";
import Agenda from "./pages/Agenda.jsx";
import Alerts from "./pages/Alerts.jsx";
import Conversations from "./pages/Conversations.jsx";
import KnowledgeBase from "./pages/KnowledgeBase.jsx";
import Login from "./pages/Login.jsx";
import Onboarding from "./pages/Onboarding.jsx";
import Profile from "./pages/Profile.jsx";
import PanelLayout from "./panel/PanelLayout.jsx";

// `?sair` no endereço encerra a sessão e mostra o login (o iniciar.bat
// abre o painel assim, para cada teste começar pela tela de login). É
// lido uma vez, ao carregar: em desenvolvimento o React roda o efeito
// de abertura duas vezes, e a segunda, já sem o `?sair`, perguntava
// "quem está logado?" antes do logout terminar e mostrava o painel por
// um instante.
const START_LOGGED_OUT = new URLSearchParams(window.location.search).has("sair");

// Sem login → tela de login. Logado sem cadastro concluído → cadastro em
// etapas. Com cadastro → painel. Quem decide é o backend, pelo `GET /auth/me`.
export default function App() {
  // undefined = ainda verificando; null = sem sessão.
  const [me, setMe] = useState(START_LOGGED_OUT ? null : undefined);
  // "Testar a SelenIA" no fim do cadastro abre o painel já no simulador.
  const [openSimulator, setOpenSimulator] = useState(false);

  const refresh = useCallback(() => {
    api
      .me()
      .then(setMe)
      .catch(() => setMe(null));
  }, []);

  const logout = useCallback(async () => {
    await api.logout().catch(() => {});
    window.google?.accounts.id.disableAutoSelect();
    setMe(null);
  }, []);

  // Qualquer chamada que volte 401 (sessão encerrada em outra aba ou
  // vencida) leva para o login.
  useEffect(() => setSessionLostHandler(() => setMe(null)), []);

  useEffect(() => {
    if (START_LOGGED_OUT) {
      window.history.replaceState(null, "", window.location.pathname);
      logout();
    } else {
      refresh();
    }
  }, [logout, refresh]);

  if (me === undefined) return null;
  if (me === null) return <Login onLogin={setMe} />;
  if (!me.professional?.onboarding_completed_at) {
    return (
      <Onboarding
        me={me}
        onLogout={logout}
        onFinished={(target) => {
          setOpenSimulator(target === "testar");
          refresh();
        }}
      />
    );
  }
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<PanelLayout me={me} onLogout={logout} startWithSimulator={openSimulator} />}>
          <Route path="/conversas" element={<Conversations />} />
          <Route path="/conversas/:conversationId" element={<Conversations />} />
          <Route path="/alertas" element={<Alerts />} />
          <Route path="/alertas/:alertId" element={<Alerts />} />
          <Route path="/agenda" element={<Agenda />} />
          <Route path="/perfil" element={<Profile />} />
          <Route path="/base-de-conhecimento" element={<KnowledgeBase />} />
          <Route path="*" element={<Navigate to="/conversas" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
