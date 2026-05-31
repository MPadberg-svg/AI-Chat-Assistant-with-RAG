import { useEffect, useRef, useState } from "react";

import SourceCitations from "./SourceCitations";

export default function ChatWindow({ messages, isLoading, sources, onSend }) {
  const [question, setQuestion] = useState("");
  const containerRef = useRef(null);

  useEffect(() => {
    containerRef.current?.scrollTo({ top: containerRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isLoading]);

  const submit = (event) => {
    event.preventDefault();
    if (!question.trim()) return;
    onSend(question);
    setQuestion("");
  };

  return (
    <section style={{ flex: 1, display: "flex", flexDirection: "column" }}>
      <div
        ref={containerRef}
        style={{
          flex: 1,
          overflowY: "auto",
          border: "1px solid #ddd",
          borderRadius: "8px",
          padding: "12px",
          background: "#fff",
        }}
      >
        {messages.map((message, index) => (
          <div
            key={index}
            style={{
              marginBottom: "8px",
              textAlign: message.role === "user" ? "right" : "left",
            }}
          >
            <span
              style={{
                display: "inline-block",
                background: message.role === "user" ? "#dff7df" : "#f4f4f4",
                borderRadius: "10px",
                padding: "8px 10px",
                maxWidth: "80%",
              }}
            >
              {message.content}
            </span>
          </div>
        ))}
        {isLoading && (
          <div style={{ marginBottom: "8px" }}>
            <span
              style={{
                display: "inline-block",
                background: "#f4f4f4",
                borderRadius: "10px",
                padding: "8px 10px",
              }}
            >
              <span style={{ opacity: 0.6 }}>Generating answer...</span>
            </span>
          </div>
        )}
        <SourceCitations sources={sources} />
      </div>
      <form onSubmit={submit} style={{ display: "flex", marginTop: "12px", gap: "8px" }}>
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask a question about your uploaded documents"
          style={{ flex: 1, padding: "10px", borderRadius: "8px", border: "1px solid #ccc" }}
        />
        <button type="submit" disabled={isLoading}>
          Send
        </button>
      </form>
    </section>
  );
}
