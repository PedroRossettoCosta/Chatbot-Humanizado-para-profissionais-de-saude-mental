import { useState } from "react";

import { api } from "../api.js";

export default function Dashboard() {
  const [slugInput, setSlugInput] = useState("");
  const [professional, setProfessional] = useState(null);
  const [voiceTone, setVoiceTone] = useState("");
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [savingTone, setSavingTone] = useState(false);
  const [toneMessage, setToneMessage] = useState("");
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");

  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [chatSessionId, setChatSessionId] = useState(null);
  const [sendingChat, setSendingChat] = useState(false);

  async function loadProfessional(event) {
    event.preventDefault();
    setLoading(true);
    setMessage("");
    try {
      const data = await api.getProfessional(slugInput.trim());
      setProfessional(data);
      setVoiceTone(data.voice_tone || "");
      const docs = await api.listDocuments(data.slug);
      setDocuments(docs);
      setChatMessages([]);
      setChatSessionId(null);
      setToneMessage("");
    } catch (err) {
      setProfessional(null);
      setDocuments([]);
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleSaveTone(event) {
    event.preventDefault();
    setSavingTone(true);
    setToneMessage("");
    try {
      const updated = await api.updateProfessional(professional.slug, { voice_tone: voiceTone });
      setProfessional(updated);
      setToneMessage("Tom de voz atualizado.");
    } catch (err) {
      setToneMessage(err.message);
    } finally {
      setSavingTone(false);
    }
  }

  async function handleUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    setUploading(true);
    setMessage("");
    try {
      const doc = await api.uploadDocument(professional.slug, file);
      setDocuments((prev) => [doc, ...prev]);
      setMessage(`"${doc.filename}" enviado e indexado.`);
    } catch (err) {
      setMessage(err.message);
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  async function handleSendChat(event) {
    event.preventDefault();
    const text = chatInput.trim();
    if (!text) return;

    setChatMessages((prev) => [...prev, { role: "user", content: text }]);
    setChatInput("");
    setSendingChat(true);
    setMessage("");
    try {
      const response = await api.sendChatMessage(professional.slug, text, chatSessionId);
      setChatSessionId(response.session_id);
      setChatMessages((prev) => {
        const next = [...prev];
        if (response.disclaimer) next.push({ role: "disclaimer", content: response.disclaimer });
        next.push({ role: "assistant", content: response.reply, sources: response.sources });
        return next;
      });
    } catch (err) {
      setMessage(err.message);
    } finally {
      setSendingChat(false);
    }
  }

  return (
    <div style={{ maxWidth: 640, margin: "40px auto", fontFamily: "sans-serif" }}>
      <h1>Chatbot Humanizado — Painel</h1>

      <form onSubmit={loadProfessional} style={{ display: "flex", gap: 8 }}>
        <input
          value={slugInput}
          onChange={(e) => setSlugInput(e.target.value)}
          placeholder="slug do profissional (ex: marilia)"
          style={{ flex: 1 }}
        />
        <button type="submit" disabled={loading || !slugInput.trim()}>
          {loading ? "Carregando..." : "Carregar"}
        </button>
      </form>

      {professional && (
        <>
          <section style={{ marginTop: 24 }}>
            <p>
              <strong>Nome:</strong> {professional.name}
            </p>
            <p>
              <strong>Slug:</strong> {professional.slug}
            </p>
          </section>

          <section style={{ marginTop: 32 }}>
            <h2>Tom de voz</h2>
            <form onSubmit={handleSaveTone}>
              <textarea
                value={voiceTone}
                onChange={(e) => setVoiceTone(e.target.value)}
                rows={4}
                style={{ width: "100%" }}
                placeholder="Ex: acolhedor, direto, sem jargões técnicos"
              />
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 8 }}>
                <button type="submit" disabled={savingTone}>
                  {savingTone ? "Salvando..." : "Salvar"}
                </button>
                {toneMessage && <span style={{ color: "#555" }}>{toneMessage}</span>}
              </div>
            </form>
          </section>

          <section style={{ marginTop: 32 }}>
            <h2>Documentos da base de conhecimento</h2>
            <input type="file" accept=".pdf,.docx,.txt,.md" onChange={handleUpload} disabled={uploading} />
            <ul>
              {documents.map((doc) => (
                <li key={doc.id}>
                  {doc.filename} — {doc.chunk_count} trechos
                </li>
              ))}
            </ul>
          </section>
          <section style={{ marginTop: 32 }}>
            <h2>Testar o chat</h2>
            <div
              style={{
                border: "1px solid #ccc",
                borderRadius: 6,
                padding: 12,
                minHeight: 120,
                maxHeight: 320,
                overflowY: "auto",
                display: "flex",
                flexDirection: "column",
                gap: 8,
              }}
            >
              {chatMessages.length === 0 && (
                <p style={{ color: "#888", margin: 0 }}>Envie uma mensagem para simular uma conversa com o bot.</p>
              )}
              {chatMessages.map((msg, i) => (
                <div key={i} style={{ textAlign: msg.role === "user" ? "right" : "left" }}>
                  <div
                    style={{
                      display: "inline-block",
                      background:
                        msg.role === "user" ? "#daf1ff" : msg.role === "disclaimer" ? "#fff6dd" : "#f0f0f0",
                      border: msg.role === "disclaimer" ? "1px solid #e8d9a0" : "none",
                      fontSize: msg.role === "disclaimer" ? 13 : undefined,
                      fontStyle: msg.role === "disclaimer" ? "italic" : undefined,
                      borderRadius: 8,
                      padding: "6px 10px",
                      maxWidth: "80%",
                    }}
                  >
                    {msg.content}
                  </div>
                  {msg.sources && msg.sources.length > 0 && (
                    <div style={{ fontSize: 12, color: "#888", marginTop: 2 }}>
                      Fontes: {msg.sources.join(", ")}
                    </div>
                  )}
                </div>
              ))}
            </div>
            <form onSubmit={handleSendChat} style={{ display: "flex", gap: 8, marginTop: 8 }}>
              <input
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Digite uma mensagem..."
                style={{ flex: 1 }}
                disabled={sendingChat}
              />
              <button type="submit" disabled={sendingChat || !chatInput.trim()}>
                {sendingChat ? "Enviando..." : "Enviar"}
              </button>
            </form>
          </section>
        </>
      )}

      {message && <p style={{ marginTop: 16, color: "#555" }}>{message}</p>}
    </div>
  );
}
