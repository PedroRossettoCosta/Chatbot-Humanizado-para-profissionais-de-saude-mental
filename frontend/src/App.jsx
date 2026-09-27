import { useCallback, useEffect, useState } from "react";

import { api } from "./api.js";
import Dashboard from "./pages/Dashboard.jsx";
import Login from "./pages/Login.jsx";
import SignupStart from "./pages/SignupStart.jsx";

// Sem login → tela de login. Logado sem cadastro → cadastro. Com
// cadastro → painel. Quem decide é o backend, pelo `GET /auth/me`.
export default function App() {
  // undefined = ainda verificando; null = sem sessão.
  const [me, setMe] = useState(undefined);

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
  if (!me.professional) return <SignupStart me={me} onCreated={refresh} onLogout={logout} />;
  return <Dashboard me={me} initialProfessional={me.professional} onLogout={logout} />;
}
