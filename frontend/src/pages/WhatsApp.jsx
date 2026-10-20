import WhatsAppConnect from "../components/WhatsAppConnect.jsx";
import { usePanel } from "../panel/PanelContext.jsx";

// WhatsApp (menu lateral): conectar o número de atendimento, para quem
// pulou a etapa 6 do cadastro, e ver como o número está na Meta.
export default function WhatsApp() {
  const { professional, onWhatsAppStatus } = usePanel();

  return (
    <div className="mx-auto max-w-3xl">
      <p className="m-0 text-xs font-semibold tracking-wider text-primary">CANAL DE ATENDIMENTO</p>
      <h1 className="m-0 mt-2 text-4xl font-bold tracking-tight text-ink">WhatsApp</h1>
      <p className="m-0 mt-3 text-base leading-relaxed text-muted">
        É neste número que a SelenIA recebe e responde as mensagens das pessoas que procuram você, pela plataforma
        oficial do WhatsApp.
      </p>
      <section className="mt-8 rounded-3xl border border-line bg-white p-6 shadow-sm sm:p-8">
        <WhatsAppConnect slug={professional.slug} defaultName={professional.name} onStatus={onWhatsAppStatus} />
      </section>
    </div>
  );
}
