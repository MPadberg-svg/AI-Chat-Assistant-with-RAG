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
    <section className="flex flex-1 flex-col">
      <div ref={containerRef} className="flex-1 space-y-3 overflow-y-auto rounded-xl border bg-white p-4">
        {messages.map((message, index) => (
          <div key={index} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
            <span
              className={
                message.role === "user"
                  ? "ml-auto max-w-xs rounded-2xl rounded-br-sm bg-blue-600 px-4 py-2 text-white"
                  : "max-w-prose rounded-2xl rounded-bl-sm bg-gray-100 px-4 py-2 text-gray-800"
              }
            >
              {message.content}
            </span>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="rounded-2xl rounded-bl-sm bg-gray-100 px-4 py-3">
              <div className="space-y-2 animate-pulse">
                <div className="h-2 w-24 rounded bg-gray-200" />
                <div className="h-2 w-32 rounded bg-gray-200" />
                <div className="h-2 w-20 rounded bg-gray-200" />
              </div>
            </div>
          </div>
        )}
        <SourceCitations sources={sources} />
      </div>
      <form onSubmit={submit} className="mt-3 flex gap-2">
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask a question about your uploaded documents"
          className="flex-1 rounded-xl border px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          type="submit"
          disabled={isLoading}
          className="rounded-xl bg-blue-600 px-5 py-2 text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </section>
  );
}
