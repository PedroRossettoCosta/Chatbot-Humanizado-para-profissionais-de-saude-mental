import { createContext, useContext } from "react";

// O que todas as telas do painel compartilham: quem está logado, a
// profissional (atualizada quando uma tela salva algo), o simulador e o
// "Sair".
export const PanelContext = createContext(null);

export function usePanel() {
  return useContext(PanelContext);
}
