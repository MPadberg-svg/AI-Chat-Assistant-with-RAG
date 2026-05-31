import { useEffect, useMemo, useState } from "react";

import ChatWindow from "./components/ChatWindow";
import DocumentUpload from "./components/DocumentUpload";
import Sidebar from "./components/Sidebar";
import { useSSE } from "./hooks/useSSE";
import { deleteDocument, listDocuments } from "./services/api";

const DEFAULT_TOP_K = 5;

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [messages, setMessages] = useState([]);
  const [conversationHistory, setConversationHistory] = useState([]);
  const [pendingQuestion, setPendingQuestion] = useState(null);
  const { answer, sources, isLoading, error, reset, startStream } = useSSE();

  const loadDocuments = async () => {
    try {
      const docs = await listDocuments();
      setDocuments(docs);
    } catch {
      setDocuments([]);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  useEffect(() => {
    if (!answer) return;
    setMessages((prev) => {
      const cloned = [...prev];
      if (cloned[cloned.length - 1]?.role === "assistant") {
        cloned[cloned.length - 1] = { role: "assistant", content: answer };
        return cloned;
      }
      return [...cloned, { role: "assistant", content: answer }];
    });
  }, [answer]);

  useEffect(() => {
    if (isLoading || !pendingQuestion) return;
    if (!error) {
      setConversationHistory((prev) => [
        ...prev,
        { role: "user", content: pendingQuestion },
        { role: "assistant", content: answer },
      ]);
    }
    setPendingQuestion(null);
  }, [answer, error, isLoading, pendingQuestion]);

  const handleSend = async (question) => {
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setPendingQuestion(question);
    await startStream(question, DEFAULT_TOP_K, conversationHistory);
  };

  const handleClear = () => {
    setMessages([]);
    setConversationHistory([]);
    setPendingQuestion(null);
    reset();
  };

  const handleUploaded = async (docId) => {
    setDocuments((prev) => Array.from(new Set([...prev, docId])));
  };

  const handleDelete = async (docId) => {
    try {
      await deleteDocument(docId);
    } catch {
      // No-op UI fallback, state still updates for immediate feedback.
    }
    setDocuments((prev) => prev.filter((id) => id !== docId));
  };

  const helperText = useMemo(() => {
    if (error) return error;
    return "Upload files, then ask grounded questions based on your documents.";
  }, [error]);

  return (
    <main style={{ fontFamily: "Arial, sans-serif", height: "100vh", display: "flex" }}>
      <Sidebar documents={documents} onDelete={handleDelete} />
      <section style={{ flex: 1, display: "flex", flexDirection: "column", padding: "16px", gap: "12px" }}>
        <h2 style={{ margin: 0 }}>RAG Chat Assistant</h2>
        <DocumentUpload onUploaded={handleUploaded} />
        <div style={{ color: error ? "#b00020" : "#555", fontSize: "13px" }}>{helperText}</div>
        <button
          type="button"
          onClick={handleClear}
          disabled={isLoading || (!messages.length && !conversationHistory.length)}
          style={{ alignSelf: "flex-start" }}
        >
          Clear conversation
        </button>
        <ChatWindow messages={messages} isLoading={isLoading} sources={sources} onSend={handleSend} />
      </section>
    </main>
  );
}
