const GOOGLE_SCRIPT = "https://accounts.google.com/gsi/client";

// Carrega o script do Google uma vez só. Serve ao botão de login e à
// janela de permissão da agenda.
let googleScript;
export function loadGoogle() {
  googleScript ||= new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = GOOGLE_SCRIPT;
    script.async = true;
    script.onload = () => resolve(window.google);
    script.onerror = () => {
      googleScript = undefined;
      reject(new Error("Não foi possível carregar o Google. Confira a conexão e tente de novo."));
    };
    document.head.appendChild(script);
  });
  return googleScript;
}
