import { useEffect, useRef, useState } from "react";

import { api } from "../api.js";
import { BookIcon, LockIcon, TrashIcon, UploadIcon } from "../components/icons.jsx";
import { Button, ErrorBox, formatDateTime } from "../components/ui.jsx";
import { usePanel } from "../panel/PanelContext.jsx";

const ACCEPTED = [".pdf", ".docx", ".txt", ".md"];

function extension(filename) {
  return filename.includes(".") ? filename.slice(filename.lastIndexOf(".")).toLowerCase() : "";
}

function TypeBadge({ filename }) {
  const ext = extension(filename).replace(".", "").toUpperCase() || "?";
  const color = ext === "PDF" ? "bg-danger-soft text-danger" : ext === "MD" ? "bg-primary-soft text-primary" : "bg-[#eff4ff] text-slate";
  return (
    <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-[11px] font-bold ${color}`}>{ext}</span>
  );
}

// Base de conhecimento (protótipo: base_de_conhecimento_maria). Os
// documentos alimentam as respostas da MarIA (RAG); a triagem de risco
// não depende deles.
export default function KnowledgeBase() {
  const { professional, openSimulator } = usePanel();
  const [documents, setDocuments] = useState(null);
  const [uploading, setUploading] = useState([]);
  const [dragging, setDragging] = useState(false);
  const [confirming, setConfirming] = useState(null);
  const [filter, setFilter] = useState("");
  const [error, setError] = useState("");
  const inputRef = useRef(null);

  useEffect(() => {
    api
      .listDocuments(professional.slug)
      .then(setDocuments)
      .catch((err) => setError(err.message));
  }, [professional.slug]);

  async function upload(files) {
    setError("");
    for (const file of files) {
      if (!ACCEPTED.includes(extension(file.name))) {
        setError(`"${file.name}": formato não aceito. Use PDF, DOCX, TXT ou MD.`);
        continue;
      }
      if (file.size > 10 * 1024 * 1024) {
        setError(`"${file.name}" passa de 10 MB.`);
        continue;
      }
      setUploading((prev) => [...prev, file.name]);
      try {
        const doc = await api.uploadDocument(professional.slug, file);
        setDocuments((prev) => [doc, ...(prev || [])]);
      } catch (err) {
        setError(`"${file.name}": ${err.message}`);
      } finally {
        setUploading((prev) => prev.filter((name) => name !== file.name));
      }
    }
  }

  async function remove(doc) {
    setError("");
    try {
      await api.deleteDocument(doc.id);
      setDocuments((prev) => prev.filter((d) => d.id !== doc.id));
    } catch (err) {
      setError(err.message);
    } finally {
      setConfirming(null);
    }
  }

  const visible = (documents || []).filter((d) => d.filename.toLowerCase().includes(filter.toLowerCase()));
  const totalChunks = (documents || []).reduce((sum, d) => sum + d.chunk_count, 0);

  return (
    <div className="mx-auto max-w-6xl">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="m-0 text-xs font-semibold tracking-wider text-primary">MATERIAL DO ATENDIMENTO</p>
          <h1 className="m-0 mt-2 text-4xl font-bold tracking-tight text-ink">Base de conhecimento</h1>
          <p className="m-0 mt-2 max-w-2xl text-muted">
            A MarIA usa estes documentos para responder dúvidas sobre o seu trabalho. Envie textos sobre sua abordagem,
            perguntas frequentes e informações práticas.
          </p>
        </div>
        <Button variant="soft" onClick={openSimulator}>
          Testar a MarIA
        </Button>
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_320px]">
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            upload([...e.dataTransfer.files]);
          }}
          className={`flex flex-col items-center justify-center rounded-3xl border-2 border-dashed px-6 py-12 text-center transition-colors ${
            dragging ? "border-primary bg-primary-soft" : "border-line bg-white"
          }`}
        >
          <span className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[#dce9ff] text-primary">
            <UploadIcon size={30} />
          </span>
          <p className="m-0 mt-4 text-lg font-semibold text-ink">Arraste arquivos ou clique para enviar</p>
          <p className="m-0 mt-1 text-sm text-muted">PDF, DOCX, TXT ou MD, até 10 MB</p>
          <Button className="mt-5" onClick={() => inputRef.current?.click()}>
            Selecionar do computador
          </Button>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED.join(",")}
            multiple
            hidden
            onChange={(e) => {
              upload([...e.target.files]);
              e.target.value = "";
            }}
          />
        </div>

        <div className="space-y-4">
          <div className="rounded-3xl border border-line bg-white p-5">
            <div className="flex gap-3">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-danger-soft text-danger">
                <LockIcon />
              </span>
              <div>
                <p className="m-0 font-semibold text-ink">Dica de privacidade</p>
                <p className="m-0 mt-1 text-sm leading-relaxed text-muted">
                  Não envie documentos com dados de pacientes. Use só material sobre o seu atendimento.
                </p>
              </div>
            </div>
          </div>
          <div className="rounded-3xl border border-line bg-white p-5">
            <p className="m-0 font-semibold text-ink">Na base agora</p>
            <p className="m-0 mt-1 text-sm text-muted">
              {documents ? `${documents.length} documento(s), ${totalChunks} trechos` : "Carregando..."}
            </p>
          </div>
        </div>
      </div>

      <div className="mt-4">
        <ErrorBox>{error}</ErrorBox>
      </div>

      <section className="mt-8 rounded-3xl border border-line bg-white">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-6 py-4">
          <h2 className="m-0 text-lg font-semibold text-ink">
            Documentos{" "}
            <span className="ml-1 rounded-full bg-[#eff4ff] px-2 py-0.5 text-sm text-slate">{documents?.length ?? 0}</span>
          </h2>
          {documents?.length > 5 && (
            <input
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filtrar pelo nome..."
              className="rounded-xl border border-line px-3 py-2 text-sm outline-none focus:border-primary"
            />
          )}
        </div>

        <ul className="m-0 p-0">
          {uploading.map((name) => (
            <li key={name} className="flex list-none items-center gap-4 border-b border-line px-6 py-4">
              <TypeBadge filename={name} />
              <span className="min-w-0 flex-1 truncate font-medium text-ink">{name}</span>
              <span className="text-sm text-primary">Processando…</span>
            </li>
          ))}
          {documents && documents.length === 0 && uploading.length === 0 && (
            <li className="flex list-none flex-col items-center px-6 py-12 text-center text-muted">
              <BookIcon size={32} />
              <p className="m-0 mt-3">Nenhum documento ainda. Envie o primeiro acima.</p>
            </li>
          )}
          {visible.map((doc) => (
            <li key={doc.id} className="flex list-none flex-wrap items-center gap-4 border-b border-line px-6 py-4 last:border-b-0">
              <TypeBadge filename={doc.filename} />
              <span className="min-w-0 flex-1 truncate font-medium text-ink" title={doc.filename}>
                {doc.filename}
              </span>
              <span className="rounded-full bg-[#eff4ff] px-3 py-1 text-xs text-slate">{doc.chunk_count} trechos</span>
              <span className="w-40 text-sm text-muted">{formatDateTime(doc.uploaded_at)}</span>
              {confirming === doc.id ? (
                <span className="flex items-center gap-2 text-sm">
                  Remover?
                  <button
                    type="button"
                    onClick={() => remove(doc)}
                    className="cursor-pointer rounded-lg border-0 bg-danger px-3 py-1 font-semibold text-white"
                  >
                    Sim
                  </button>
                  <button
                    type="button"
                    onClick={() => setConfirming(null)}
                    className="cursor-pointer rounded-lg border-0 bg-[#eff4ff] px-3 py-1 text-slate"
                  >
                    Não
                  </button>
                </span>
              ) : (
                <button
                  type="button"
                  onClick={() => setConfirming(doc.id)}
                  className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-xl border-0 bg-transparent text-muted transition-colors hover:bg-danger-soft hover:text-danger"
                  aria-label={`Remover ${doc.filename}`}
                  title="Remover documento"
                >
                  <TrashIcon size={18} />
                </button>
              )}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
