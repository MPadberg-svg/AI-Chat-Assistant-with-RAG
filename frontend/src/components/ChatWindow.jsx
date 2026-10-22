import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";

import SourceCitations from "./SourceCitations";

const INLINE_CODE_CLASS = "rounded bg-gray-100 px-1 font-mono text-sm";
const BLOCK_CLASS = "block overflow-x-auto rounded-lg bg-gray-900 p-3 text-sm text-green-400";

// react-markdown v10 no longer passes an `inline` flag to code components.
// Fenced blocks always carry a className (e.g. "language-js"), inline spans do
// not, so block styling is applied on `pre` and inline styling on `code`.
const markdownComponents = {
  pre({ children }) {
    return <pre className={BLOCK_CLASS}>{children}</pre>;
  },
  code({ className, children, ...props }) {
    return (
      <code className={className || INLINE_CODE_CLASS} {...props}>
        {children}
      </code>
    );
  },
  a({ children, ...props }) {
    return (
      <a target="_blank" rel="noopener noreferrer" {...props}>
        {children}
      </a>
    );
  },
};

export default function ChatWindow({ messages, isLoading, streamingAnswer = "", sources, onSend }) {
  const [question, setQuestion] = useState("");
  const containerRef = useRef(null);
  // While a response streams it is rendered here, not in `messages`; the
  // parent commits it to the transcript once the stream completes.
  const showStreamingBubble = isLoading && Boolean(streamingAnswer);
  const showTypingIndicator = isLoading && !streamingAnswer;

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
  }, [messages, isLoading, streamingAnswer]);

  const submit = (event) => {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || isLoading) return;
    onSend(trimmed);
    setQuestion("");
  };

  return (
    <section className="flex flex-1 flex-col">
      <div
        ref={containerRef}
        role="log"
        aria-live="polite"
        className="flex-1 space-y-3 overflow-y-auto rounded-xl border bg-white p-4"
      >
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
          >
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
        {showStreamingBubble && (
          <div className="flex justify-start">
            <div className="max-w-prose rounded-2xl rounded-bl-sm bg-gray-100 px-4 py-2 text-gray-800">
              <div className="prose prose-sm max-w-none">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeHighlight]}
                  components={markdownComponents}
                >
                  {streamingAnswer}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        )}
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
          aria-label="Your question"
          className="flex-1 rounded-xl border px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          type="submit"
          disabled={isLoading || !question.trim()}
          className="rounded-xl bg-blue-600 px-5 py-2 text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
        >
          {isLoading ? "Sending…" : "Send"}
        </button>
      </form>
    </section>
  );
}
