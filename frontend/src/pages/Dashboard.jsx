import { useEffect, useState } from "react";

import { api } from "../api.js";

const STATE_LABELS = {
  active: "🤖 MarIA respondendo",
  human: "🙋 Você está no controle (MarIA em silêncio)",
  emergency_hold: "🚨 Em espera após alerta de emergência (MarIA em silêncio)",
};

// Painel provisório (visual antigo): é refeito tela a tela no visual do
// protótipo ao longo da semana 2. Recebe a profissional da conta logada.
export default function Dashboard({ me, initialProfessional, onLogout, openSimulator }) {
  const [professional, setProfessional] = useState(null);
  const [voiceTone, setVoiceTone] = useState("");
  const [audience, setAudience] = useState("");
  const [alertEmail, setAlertEmail] = useState("");
  const [serviceInfo, setServiceInfo] = useState("");
  const [voiceExamples, setVoiceExamples] = useState({});
  const [extraNeverSay, setExtraNeverSay] = useState("");
  const [guidelines, setGuidelines] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [savingTone, setSavingTone] = useState(false);
  const [toneMessage, setToneMessage] = useState("");
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");

  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [chatSessionId, setChatSessionId] = useState(null);
  const [sendingChat, setSendingChat] = useState(false);
  // Handoff: conversa do simulador e quem está no controle dela.
  const [conversationId, setConversationId] = useState(null);
  const [conversationState, setConversationState] = useState(null);
  const [professionalInput, setProfessionalInput] = useState("");
  const [sessionMinutes, setSessionMinutes] = useState("50");

  // Regras fixas da MarIA (perguntas de tom e "nunca dizer" do produto).
  useEffect(() => {
    api.getGuidelines().then(setGuidelines).catch((err) => setMessage(err.message));
  }, []);

  function setExample(key, field, value) {
    setVoiceExamples((prev) => ({ ...prev, [key]: { ...prev[key], [field]: value } }));
  }

  useEffect(() => {
    loadProfessional(initialProfessional);
  }, [initialProfessional]);

  useEffect(() => {
    if (openSimulator && professional) document.getElementById("testar-chat")?.scrollIntoView({ behavior: "smooth" });
  }, [openSimulator, professional]);

  async function loadProfessional(data) {
    setMessage("");
    try {
      setProfessional(data);
      setVoiceTone(data.voice_tone || "");
      setAudience(data.audience_description || "");
      setAlertEmail(data.alert_email || "");
      setServiceInfo(data.service_info || "");
      setVoiceExamples(data.voice_examples || {});
      setExtraNeverSay((data.extra_never_say || []).join("\n"));
      const docs = await api.listDocuments(data.slug);
      setDocuments(docs);
      setChatMessages([]);
      setChatSessionId(null);
      setConversationId(null);
      setConversationState(null);
      setToneMessage("");
    } catch (err) {
      setDocuments([]);
      setMessage(err.message);
    }
  }

  async function handleSaveTone(event) {
    event.preventDefault();
    setSavingTone(true);
    setToneMessage("");
    try {
      const updated = await api.updateProfessional(professional.slug, {
        voice_tone: voiceTone,
        alert_email: alertEmail,
        audience_description: audience,
        service_info: serviceInfo,
        voice_examples: voiceExamples,
        // Um item por linha; linhas vazias são descartadas no backend.
        extra_never_say: extraNeverSay.split("\n"),
      });
      setProfessional(updated);
      setToneMessage("Perfil atualizado.");
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
      setConversationId(response.conversation_id);
      setConversationState(response.state);
      setChatMessages((prev) => {
        const next = [...prev];
        if (response.disclaimer) next.push({ role: "disclaimer", content: response.disclaimer });
        // Sem resposta: o bot está em silêncio (alerta ou profissional no controle).
        if (response.reply) next.push({ role: "assistant", content: response.reply, sources: response.sources });
        return next;
      });
    } catch (err) {
      setMessage(err.message);
    } finally {
      setSendingChat(false);
    }
  }

  async function handleSessionToggle() {
    setMessage("");
    try {
      const updated = professional.in_session
        ? await api.endSession(professional.slug)
        : await api.startSession(professional.slug, sessionMinutes ? Number(sessionMinutes) : null);
      setProfessional(updated);
    } catch (err) {
      setMessage(err.message);
    }
  }

  async function handleConversationAction(action) {
    setMessage("");
    try {
      const conversation =
        action === "take-over" ? await api.takeOver(conversationId) : await api.releaseToBot(conversationId);
      setConversationState(conversation.state);
    } catch (err) {
      setMessage(err.message);
    }
  }

  async function handleProfessionalReply(event) {
    event.preventDefault();
    const text = professionalInput.trim();
    if (!text) return;
    setMessage("");
    try {
      const conversation = await api.sendProfessionalMessage(conversationId, text);
      setConversationState(conversation.state);
      setChatMessages((prev) => [...prev, { role: "professional", content: text }]);
      setProfessionalInput("");
    } catch (err) {
      setMessage(err.message);
    }
  }

  return (
    <div style={{ maxWidth: 640, margin: "40px auto", fontFamily: "sans-serif" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
        <h1 style={{ margin: 0 }}>MarIA — Painel</h1>
        <div style={{ fontSize: 14, color: "#555" }}>
          {me.email} ·{" "}
          <button type="button" onClick={onLogout}>
            Sair
          </button>
        </div>
      </div>

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

          <section
            style={{
              marginTop: 16,
              padding: 12,
              borderRadius: 6,
              border: "1px solid #ddd",
              background: professional.in_session ? "#eef7ee" : undefined,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
              <strong>{professional.in_session ? "🟢 Em consulta" : "Disponível"}</strong>
              {professional.in_session && (
                <span style={{ color: "#555", fontSize: 13 }}>
                  {professional.in_session_until
                    ? `até ${new Date(professional.in_session_until).toLocaleTimeString("pt-BR", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}`
                    : "até você desligar"}
                </span>
              )}
              {!professional.in_session && (
                <select
                  value={sessionMinutes}
                  onChange={(e) => setSessionMinutes(e.target.value)}
                  aria-label="Duração"
                >
                  <option value="50">50 min</option>
                  <option value="90">1h30</option>
                  <option value="">até eu desligar</option>
                </select>
              )}
              <button type="button" onClick={handleSessionToggle}>
                {professional.in_session ? "Encerrar" : "Entrar em consulta"}
              </button>
            </div>
            <p style={{ margin: "6px 0 0", color: "#555", fontSize: 13 }}>
              Em consulta, quem pedir para falar com você recebe um aviso de que você está em atendimento, e a
              MarIA oferece ajuda enquanto isso. Emergências continuam gerando alerta na hora.
            </p>
          </section>

          <section style={{ marginTop: 32 }}>
            <h2>Perfil do atendimento</h2>
            <form onSubmit={handleSaveTone}>
              <label htmlFor="alert-email">
                <strong>E-mail para alertas</strong>
              </label>
              <p style={{ margin: "4px 0", color: "#555", fontSize: 13 }}>
                Você recebe um e-mail na hora quando houver emergência, dúvida sobre segurança ou alguém
                pedir para não falar com a MarIA. O e-mail não traz o conteúdo da conversa.
              </p>
              <input
                id="alert-email"
                type="email"
                value={alertEmail}
                onChange={(e) => setAlertEmail(e.target.value)}
                style={{ width: "100%", marginBottom: 12 }}
                placeholder="voce@exemplo.com"
              />
              <label htmlFor="audience">
                <strong>Especialidade e público</strong>
              </label>
              <p style={{ margin: "4px 0", color: "#555", fontSize: 13 }}>
                Ajuda a MarIA a entender o que é comum no seu consultório. Não muda os critérios de
                emergência, que são iguais em todas as contas.
              </p>
              <textarea
                id="audience"
                value={audience}
                onChange={(e) => setAudience(e.target.value)}
                rows={3}
                style={{ width: "100%" }}
                placeholder="Ex: psicanalista; atendo principalmente pessoas em sofrimento por relacionamentos (término, traição, dependência emocional)"
              />
              <label htmlFor="service-info" style={{ display: "block", marginTop: 12 }}>
                <strong>Atendimento e valores</strong>
              </label>
              <p style={{ margin: "4px 0", color: "#555", fontSize: 13 }}>
                A MarIA informa o valor já na primeira resposta a quem perguntar o preço.
              </p>
              <textarea
                id="service-info"
                value={serviceInfo}
                onChange={(e) => setServiceInfo(e.target.value)}
                rows={4}
                style={{ width: "100%" }}
                placeholder="Ex: online pelo Google Meet, sessões semanais de 50 minutos, R$ 200 por sessão no Pix"
              />
              <label htmlFor="voice-tone" style={{ display: "block", marginTop: 12 }}>
                <strong>Tom de voz</strong>
              </label>
              <textarea
                id="voice-tone"
                value={voiceTone}
                onChange={(e) => setVoiceTone(e.target.value)}
                rows={4}
                style={{ width: "100%" }}
                placeholder="Ex: acolhedor, direto, sem jargões técnicos"
              />

              {guidelines && (
                <>
                  <h3 style={{ marginTop: 20, marginBottom: 4 }}>Exemplos de resposta</h3>
                  <p style={{ margin: "4px 0", color: "#555", fontSize: 13 }}>
                    Para cada pergunta, escreva uma resposta como você gostaria que a MarIA respondesse e
                    outra que você não quer. Ela imita o estilo da boa e evita o da ruim.
                  </p>
                  {guidelines.voice_questions.map((q) => (
                    <fieldset key={q.key} style={{ marginTop: 8, border: "1px solid #ddd", borderRadius: 6 }}>
                      <legend>"{q.question}"</legend>
                      <textarea
                        aria-label={`Resposta boa: ${q.question}`}
                        value={voiceExamples[q.key]?.good || ""}
                        onChange={(e) => setExample(q.key, "good", e.target.value)}
                        rows={3}
                        style={{ width: "100%" }}
                        placeholder="Resposta boa"
                      />
                      <textarea
                        aria-label={`Resposta ruim: ${q.question}`}
                        value={voiceExamples[q.key]?.bad || ""}
                        onChange={(e) => setExample(q.key, "bad", e.target.value)}
                        rows={2}
                        style={{ width: "100%", marginTop: 4 }}
                        placeholder="Resposta ruim"
                      />
                    </fieldset>
                  ))}

                  <h3 style={{ marginTop: 20, marginBottom: 4 }}>O que a MarIA nunca diz</h3>
                  <p style={{ margin: "4px 0", color: "#555", fontSize: 13 }}>
                    Regras fixas, iguais em todas as contas:
                  </p>
                  <ul style={{ margin: "4px 0", color: "#555", fontSize: 13 }}>
                    {guidelines.never_say.map((item) => (
                      <li key={item}>🔒 {item}</li>
                    ))}
                  </ul>
                  <label htmlFor="extra-never-say" style={{ display: "block", marginTop: 8 }}>
                    <strong>Acrescentar regras suas</strong> (uma por linha)
                  </label>
                  <textarea
                    id="extra-never-say"
                    value={extraNeverSay}
                    onChange={(e) => setExtraNeverSay(e.target.value)}
                    rows={3}
                    style={{ width: "100%" }}
                    placeholder="Ex: não comentar o trabalho de colegas"
                  />
                </>
              )}
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
          <section id="testar-chat" style={{ marginTop: 32 }}>
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
                  {msg.role === "professional" && (
                    <div style={{ fontSize: 12, color: "#2e7d32", marginBottom: 2 }}>{professional.name} (pelo painel)</div>
                  )}
                  <div
                    style={{
                      display: "inline-block",
                      background:
                        msg.role === "user"
                          ? "#daf1ff"
                          : msg.role === "disclaimer"
                            ? "#fff6dd"
                            : msg.role === "professional"
                              ? "#e3f4e4"
                              : "#f0f0f0",
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

            {conversationId && (
              <div style={{ marginTop: 12, padding: 12, border: "1px dashed #bbb", borderRadius: 6 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                  <strong style={{ fontSize: 14 }}>Como profissional:</strong>
                  <span style={{ fontSize: 13, color: "#555" }}>{STATE_LABELS[conversationState]}</span>
                  {conversationState === "active" && (
                    <button type="button" onClick={() => handleConversationAction("take-over")}>
                      Assumir conversa
                    </button>
                  )}
                  {conversationState !== "active" && (
                    <button type="button" onClick={() => handleConversationAction("release")}>
                      Devolver ao bot
                    </button>
                  )}
                </div>
                <form onSubmit={handleProfessionalReply} style={{ display: "flex", gap: 8, marginTop: 8 }}>
                  <input
                    value={professionalInput}
                    onChange={(e) => setProfessionalInput(e.target.value)}
                    placeholder={`Responder como ${professional.name}...`}
                    style={{ flex: 1 }}
                  />
                  <button type="submit" disabled={!professionalInput.trim()}>
                    Responder
                  </button>
                </form>
              </div>
            )}
          </section>
        </>
      )}

      {message && <p style={{ marginTop: 16, color: "#555" }}>{message}</p>}
    </div>
  );
}
