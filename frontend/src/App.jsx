import { useCallback, useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { api } from "./api.js";
import Conversations from "./pages/Conversations.jsx";
import KnowledgeBase from "./pages/KnowledgeBase.jsx";
import Login from "./pages/Login.jsx";
import Onboarding from "./pages/Onboarding.jsx";
import Profile from "./pages/Profile.jsx";
import PanelLayout from "./panel/PanelLayout.jsx";

// Sem login → tela de login. Logado sem cadastro concluído → cadastro em
// etapas. Com cadastro → painel. Quem decide é o backend, pelo `GET /auth/me`.
export default function App() {
  // undefined = ainda verificando; null = sem sessão.
  const [me, setMe] = useState(undefined);
  // "Testar a MarIA" no fim do cadastro abre o painel já no simulador.
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

  // `?sair` no endereço encerra a sessão e mostra o login. O iniciar.bat
  // abre o painel assim, para cada teste começar pela tela de login.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.has("sair")) {
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
          <Route path="/perfil" element={<Profile />} />
          <Route path="/base-de-conhecimento" element={<KnowledgeBase />} />
          <Route path="*" element={<Navigate to="/conversas" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
