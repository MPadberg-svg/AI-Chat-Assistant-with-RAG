import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import ChatWindow from "./ChatWindow";
import SourceCitations from "./SourceCitations";

const render = (content, sources = []) =>
  renderToStaticMarkup(
    <ChatWindow
      messages={[{ role: "assistant", content }]}
      isLoading={false}
      sources={sources}
      onSend={() => {}}
    />
  );

describe("ChatWindow markdown rendering", () => {
  it("renders inline code as <code>, not a block", () => {
    const html = render("Run `npm ci` first.");

    expect(html).toContain("Run <code");
    expect(html).not.toContain("<pre>npm ci</pre>");
  });

  it("does not nest <pre> inside <pre> for fenced blocks", () => {
    const html = render("```js\nconst x = 1;\n```");

    expect(html).not.toContain("<pre><pre");
    expect(html).toContain("language-js");
  });

  it("keeps paragraphs that were separated by blank lines", () => {
    const html = render("First paragraph.\n\nSecond paragraph.");

    expect(html.match(/<p>/g)).toHaveLength(2);
    expect(html).toContain("First paragraph.");
    expect(html).toContain("Second paragraph.");
  });

  it("opens links safely in a new tab", () => {
    const html = render("[docs](https://example.com)");

    expect(html).toContain('target="_blank"');
    expect(html).toContain('rel="noopener noreferrer"');
  });
});

describe("SourceCitations", () => {
  const renderSources = (sources) =>
    renderToStaticMarkup(<SourceCitations sources={sources} />);

  it("renders a percentage for a valid score", () => {
    const html = renderSources([
      { doc_id: "a", filename: "runbook.pdf", page: 3, score: 0.75 },
    ]);

    expect(html).toContain("runbook.pdf · p.3 · 75%");
  });

  it("clamps out-of-range scores instead of printing negatives", () => {
    const html = renderSources([
      { doc_id: "a", filename: "x.pdf", page: 1, score: -12.5 },
      { doc_id: "b", filename: "y.pdf", page: 2, score: 4 },
    ]);

    expect(html).toContain("x.pdf · p.1 · 0%");
    expect(html).toContain("y.pdf · p.2 · 100%");
    expect(html).not.toContain("· -");
    expect(html).not.toContain("Infinity");
    expect(html).not.toContain("NaN");
  });

  it("renders nothing when there are no sources", () => {
    expect(renderSources([])).toBe("");
  });
});
