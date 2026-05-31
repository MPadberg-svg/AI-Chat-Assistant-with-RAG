import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000/api",
});

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

export const sendMessage = async (question, top_k = 5, history = []) => {
  return fetch(`${api.defaults.baseURL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k, history }),
  });
};

export default api;
