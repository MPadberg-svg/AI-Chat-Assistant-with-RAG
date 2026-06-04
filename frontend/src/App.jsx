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

  const handleSend = async (question) => {
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    const finalAnswer = await startStream(question, DEFAULT_TOP_K, conversationHistory);
    if (finalAnswer !== null) {
      setConversationHistory((prev) => [
        ...prev,
        { role: "user", content: question },
        { role: "assistant", content: finalAnswer },
      ]);
    }
  };

  const handleClear = () => {
    setMessages([]);
    setConversationHistory([]);
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
    <main className="flex h-screen font-sans">
      <Sidebar documents={documents} onDelete={handleDelete} />
      <section className="flex flex-1 flex-col gap-3 bg-gray-50 p-4">
        <h2 className="text-xl font-semibold">🧠 RAG Chat Assistant</h2>
        <DocumentUpload onUploaded={handleUploaded} />
        <div className={`text-sm ${error ? "text-red-600" : "text-gray-600"}`}>{helperText}</div>
        <button
          type="button"
          onClick={handleClear}
          disabled={isLoading || (!messages.length && !conversationHistory.length)}
          className="self-start text-sm font-medium text-blue-600 transition-colors hover:text-blue-700 disabled:opacity-50"
        >
          Clear conversation
        </button>
        <ChatWindow messages={messages} isLoading={isLoading} sources={sources} onSend={handleSend} />
      </section>
    </main>
  );
}