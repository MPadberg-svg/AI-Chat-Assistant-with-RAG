import axios from "axios";

// Same-origin by default: nginx proxies /api to the backend in production and
// Vite proxies it in development. Set VITE_API_URL only for split deployments.
const BASE_URL = import.meta.env.VITE_API_URL || "/api";

const api = axios.create({ baseURL: BASE_URL });

/** Turn a failed response into a human-readable message. */
export async function readErrorMessage(response) {
  const contentType = response.headers?.get?.("content-type") || "";
  if (contentType.includes("application/json")) {
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") return body.detail;
      if (Array.isArray(body?.detail)) {
        return body.detail.map((item) => item.msg || String(item)).join(", ");
      }
    } catch {
      // fall through to the generic message
    }
  }
  return `Request failed (${response.status})`;
}

export const uploadDocument = async (file, onUploadProgress) => {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post("/documents/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress,
  });
  return response.data;
};

export const listDocuments = async () => {
  const response = await api.get("/documents");
  return response.data;
};

export const deleteDocument = async (docId) => {
  await api.delete(`/documents/${encodeURIComponent(docId)}`);
};

export const sendMessage = async (question, topK = 5, history = [], signal) => {
  return fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k: topK, history }),
    signal,
  });
};

export default api;
