const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function request(path, { method = "GET", body, isFormData = false } = {}) {
  const headers = {};
  if (body && !isFormData) headers["Content-Type"] = "application/json";

  const response = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: isFormData ? body : body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || `Erro ${response.status}`);
  }

  if (response.status === 204) return null;
  return response.json();
}

export const api = {
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
};
