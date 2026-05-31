import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";

import SourceCitations from "./SourceCitations";

export default function ChatWindow({ messages, isLoading, sources, onSend }) {
  const [question, setQuestion] = useState("");
  const containerRef = useRef(null);
  const lastAssistantMessage = [...messages].reverse().find((message) => message.role === "assistant");
  const showTypingIndicator = isLoading && (!lastAssistantMessage || !lastAssistantMessage.content?.length);

  const markdownComponents = {
    code({ inline, className, children, ...props }) {
      if (inline) {
        return (
          <code className="rounded bg-gray-100 px-1 font-mono text-sm" {...props}>
            {children}
          </code>
        );
      }
      return (
        <pre className="block overflow-x-auto rounded-lg bg-gray-900 p-3 text-sm text-green-400">
          <code className={className} {...props}>
            {children}
          </code>
        </pre>
      );
    },
  };

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
            {message.role === "user" ? (
              <span className="ml-auto max-w-xs rounded-2xl rounded-br-sm bg-blue-600 px-4 py-2 text-white">
                {message.content}
              </span>
            ) : (
              <div className="max-w-prose rounded-2xl rounded-bl-sm bg-gray-100 px-4 py-2 text-gray-800">
                <div className="prose prose-sm max-w-none">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    rehypePlugins={[rehypeHighlight]}
                    components={markdownComponents}
                  >
                    {message.content}
                  </ReactMarkdown>
                </div>
              </div>
            )}
          </div>
        ))}
        {showTypingIndicator && (
          <div className="flex justify-start">
            <div className="max-w-prose rounded-2xl rounded-bl-sm bg-gray-100 px-4 py-2 text-gray-800">
              <div className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-gray-400 animate-bounce delay-0" />
                <span className="h-2 w-2 rounded-full bg-gray-400 animate-bounce delay-75" />
                <span className="h-2 w-2 rounded-full bg-gray-400 animate-bounce delay-150" />
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
