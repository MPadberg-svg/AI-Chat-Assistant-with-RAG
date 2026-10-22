import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import App from "./App";
import ErrorBoundary from "./components/ErrorBoundary";

describe("application render smoke test", () => {
  it("renders the whole application tree without throwing", () => {
    const html = renderToStaticMarkup(<App />);

    expect(html).toContain("RAG Chat Assistant");
    expect(html).toContain("Clear conversation");
    expect(html).toContain("Uploaded documents");
  });
});

describe("ErrorBoundary", () => {
  it("renders its children while there is no error", () => {
    const html = renderToStaticMarkup(
      <ErrorBoundary>
        <p>healthy child</p>
      </ErrorBoundary>,
    );

    expect(html).toContain("healthy child");
    expect(html).not.toContain("Something went wrong");
  });

  it("derives error state from a thrown error", () => {
    // Error boundaries only catch during client rendering, so this state
    // transition is asserted directly rather than via a throwing child.
    const error = new Error("kaboom");

    expect(ErrorBoundary.getDerivedStateFromError(error)).toEqual({ error });
  });
});
