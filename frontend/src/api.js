// A API responde em /api, no mesmo endereço do painel (proxy do Vite em
// desenvolvimento). O cookie de sessão vai junto em toda chamada.
const API_URL = import.meta.env.VITE_API_URL || "/api";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
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

  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    const message = typeof detail.detail === "string" ? detail.detail : `Erro ${response.status}`;
    throw new ApiError(message, response.status);
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
  getGuidelines: () => request("/assistant/guidelines"),
  getProfessional: (slug) => request(`/professionals/${slug}`),
  updateProfessional: (slug, payload) => request(`/professionals/${slug}`, { method: "PATCH", body: payload }),
  listDocuments: (slug) => request(`/documents/${slug}`),
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
  takeOver: (conversationId) => request(`/conversations/${conversationId}/take-over`, { method: "POST" }),
  releaseToBot: (conversationId) => request(`/conversations/${conversationId}/release`, { method: "POST" }),
  sendProfessionalMessage: (conversationId, content) =>
    request(`/conversations/${conversationId}/messages`, { method: "POST", body: { content } }),
};
