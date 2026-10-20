// A API responde em /api, no mesmo endereço do painel (proxy do Vite em
// desenvolvimento). O cookie de sessão vai junto em toda chamada.
const API_URL = import.meta.env.VITE_API_URL || "/api";

export class ApiError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.status = status;
    // Corpo do erro, quando é mais que uma frase (ex.: lista do que falta no cadastro).
    this.detail = detail;
  }
}

// Sessão encerrada fora desta aba (Sair em outra aba, `?sair` do
// iniciar.bat, validade vencida): o App volta para a tela de login em vez
// de deixar o painel aberto respondendo "Faça login" em cada tela.
let onSessionLost = () => {};
// Endereço do arquivo (foto, áudio, documento) que a pessoa mandou. O
// backend busca na Meta na hora; o cookie de sessão vai junto porque é o
// mesmo endereço do painel.
export function mediaUrl(conversationId, messageId) {
  return `${API_URL}/conversations/${conversationId}/messages/${messageId}/media`;
}

export function setSessionLostHandler(handler) {
  onSessionLost = handler;
}

async function request(path, { method = "GET", body, isFormData = false } = {}) {
  const headers = {};
  if (body && !isFormData) headers["Content-Type"] = "application/json";

  const response = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: isFormData ? body : body ? JSON.stringify(body) : undefined,
    credentials: "include",
  });

  // No login com o Google, 401 é credencial recusada, não sessão perdida.
  if (response.status === 401 && path !== "/auth/google") onSessionLost();

  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    const message =
      typeof detail.detail === "string" ? detail.detail : detail.detail?.message || `Erro ${response.status}`;
    throw new ApiError(message, response.status, detail.detail);
  }

  if (response.status === 204) return null;
  return response.json();
}

export const api = {
  getAuthConfig: () => request("/auth/config"),
  loginWithGoogle: (credential) => request("/auth/google", { method: "POST", body: { credential } }),
  me: () => request("/auth/me"),
  logout: () => request("/auth/logout", { method: "POST" }),
  createProfessional: (payload) => request("/professionals", { method: "POST", body: payload }),
  acceptRules: (slug) => request(`/professionals/${slug}/accept-rules`, { method: "POST" }),
  completeOnboarding: (slug) => request(`/professionals/${slug}/complete-onboarding`, { method: "POST" }),
  getGuidelines: () => request("/assistant/guidelines"),
  getProfessional: (slug) => request(`/professionals/${slug}`),
  updateProfessional: (slug, payload) => request(`/professionals/${slug}`, { method: "PATCH", body: payload }),
  listDocuments: (slug) => request(`/documents/${slug}`),
  deleteDocument: (documentId) => request(`/documents/${documentId}`, { method: "DELETE" }),
  uploadDocument: (slug, file) => {
    const formData = new FormData();
    formData.append("professional_slug", slug);
    formData.append("file", file);
    return request("/documents/upload", { method: "POST", body: formData, isFormData: true });
  },
  sendChatMessage: (slug, message, sessionId) =>
    request("/chat/simulate", {
      method: "POST",
      body: { professional_slug: slug, message, session_id: sessionId || null },
    }),
  // minutes nulo = "Em consulta" até desligar.
  startSession: (slug, minutes) => request(`/professionals/${slug}/in-session`, { method: "PUT", body: { minutes } }),
  endSession: (slug) => request(`/professionals/${slug}/in-session`, { method: "DELETE" }),
  listConversations: (slug) => request(`/conversations?professional_slug=${encodeURIComponent(slug)}`),
  getConversation: (conversationId) => request(`/conversations/${conversationId}`),
  listAlerts: (slug) => request(`/alerts?professional_slug=${encodeURIComponent(slug)}`),
  getAlert: (alertId) => request(`/alerts/${alertId}`),
  viewAlert: (alertId) => request(`/alerts/${alertId}/view`, { method: "POST" }),
  reviewAlert: (alertId, note) => request(`/alerts/${alertId}/review`, { method: "POST", body: { note: note || null } }),
  takeOver: (conversationId) => request(`/conversations/${conversationId}/take-over`, { method: "POST" }),
  releaseToBot: (conversationId) => request(`/conversations/${conversationId}/release`, { method: "POST" }),
  getCalendar: (slug) => request(`/calendar/${slug}`),
  connectCalendar: (slug, code) => request(`/calendar/${slug}/connect`, { method: "POST", body: { code } }),
  disconnectCalendar: (slug) => request(`/calendar/${slug}/connect`, { method: "DELETE" }),
  getFreeSlots: (slug) => request(`/calendar/${slug}/free-slots`),
  listAppointments: (slug) => request(`/calendar/${slug}/appointments`),
  getEvents: (slug, start) => request(`/calendar/${slug}/events?start=${start}`),
  createEvent: (slug, payload) => request(`/calendar/${slug}/events`, { method: "POST", body: payload }),
  approveAppointment: (id) => request(`/calendar/appointments/${id}/approve`, { method: "POST" }),
  rejectAppointment: (id) => request(`/calendar/appointments/${id}/reject`, { method: "POST" }),
  getWhatsApp: (slug) => request(`/professionals/${slug}/whatsapp`),
  startWhatsApp: (slug, number, displayName, method) =>
    request(`/professionals/${slug}/whatsapp`, {
      method: "POST",
      body: { number, display_name: displayName, method },
    }),
  resendWhatsAppCode: (slug, method) => request(`/professionals/${slug}/whatsapp/resend`, { method: "POST", body: { method } }),
  verifyWhatsApp: (slug, code) => request(`/professionals/${slug}/whatsapp/verify`, { method: "POST", body: { code } }),
  registerWhatsApp: (slug) => request(`/professionals/${slug}/whatsapp/register`, { method: "POST" }),
  cancelWhatsApp: (slug) => request(`/professionals/${slug}/whatsapp/pending`, { method: "DELETE" }),
  renameWhatsApp: (slug, displayName) =>
    request(`/professionals/${slug}/whatsapp/name`, { method: "POST", body: { display_name: displayName } }),
  applyWhatsAppName: (slug) => request(`/professionals/${slug}/whatsapp/name/apply`, { method: "POST" }),
  disconnectWhatsApp: (slug) => request(`/professionals/${slug}/whatsapp`, { method: "DELETE" }),
  listClients: (slug) => request(`/clients?professional_slug=${encodeURIComponent(slug)}`),
  // { active } e/ou { allow_special_hours }.
  updateClient: (contactId, payload) => request(`/clients/${contactId}`, { method: "PATCH", body: payload }),
  sendProfessionalMessage: (conversationId, content) =>
    request(`/conversations/${conversationId}/messages`, { method: "POST", body: { content } }),
};
