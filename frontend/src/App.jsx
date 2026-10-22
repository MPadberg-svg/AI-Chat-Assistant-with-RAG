import { useCallback, useEffect, useMemo, useState } from "react";

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
  const [notice, setNotice] = useState("");
  const { answer, sources, isLoading, error, reset, startStream, cancel } = useSSE();

  const loadDocuments = useCallback(async () => {
    try {
      const docs = await listDocuments();
      setDocuments(Array.isArray(docs) ? docs : []);
    } catch {
      setDocuments([]);
      setNotice("Could not load your documents. Is the backend running?");
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  useEffect(() => {
    if (!answer) return;
    setMessages((previous) => {
      const next = [...previous];
      if (next[next.length - 1]?.role === "assistant") {
        next[next.length - 1] = { role: "assistant", content: answer };
        return next;
      }
      return [...next, { role: "assistant", content: answer }];
    });
  }, [answer]);

  const handleSend = async (question) => {
    setNotice("");
    setMessages((previous) => [...previous, { role: "user", content: question }]);
    const finalAnswer = await startStream(question, DEFAULT_TOP_K, conversationHistory);
    if (finalAnswer !== null) {
      setConversationHistory((previous) => [
        ...previous,
        { role: "user", content: question },
        { role: "assistant", content: finalAnswer },
      ]);
    }
  };

  const handleClear = () => {
    cancel();
    setMessages([]);
    setConversationHistory([]);
    setNotice("");
    reset();
  };

  const handleUploaded = async () => {
    setNotice("");
    await loadDocuments();
  };

  const handleDelete = async (docId) => {
    try {
      await deleteDocument(docId);
    } catch {
      setNotice("Could not delete that document. Please try again.");
      return;
    }
    setDocuments((previous) => previous.filter((doc) => doc.doc_id !== docId));
  };

  const helperText = useMemo(() => {
    if (error) return error;
    if (notice) return notice;
    return "Upload files, then ask grounded questions based on your documents.";
  }, [error, notice]);

  return (
    <main className="flex h-screen font-sans">
      <Sidebar documents={documents} onDelete={handleDelete} />
      <section className="flex flex-1 flex-col gap-3 bg-gray-50 p-4">
        <h2 className="text-xl font-semibold">🧠 RAG Chat Assistant</h2>
        <DocumentUpload onUploaded={handleUploaded} />
        <div
          className={`text-sm ${error || notice ? "text-red-600" : "text-gray-600"}`}
          role={error || notice ? "alert" : undefined}
        >
          {helperText}
        </div>
        <button
          type="button"
          onClick={handleClear}
          disabled={!messages.length && !conversationHistory.length}
          className="self-start text-sm font-medium text-blue-600 transition-colors hover:text-blue-700 disabled:opacity-50"
        >
          Clear conversation
        </button>
        <ChatWindow
          messages={messages}
          isLoading={isLoading}
          sources={sources}
          onSend={handleSend}
        />
      </section>
    </main>
  );
}
