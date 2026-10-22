import { describe, expect, it } from "vitest";

import { createSseParser, parseFrame } from "./sse";

const collect = () => {
  const events = [];
  const parser = createSseParser((event) => events.push(event));
  return { events, parser };
};

describe("parseFrame", () => {
  it("reads event and data fields", () => {
    expect(parseFrame("event: token\ndata: hello")).toEqual({
      event: "token",
      data: "hello",
    });
  });

  it("joins multiple data lines with newlines", () => {
    expect(parseFrame("event: token\ndata: a\ndata: b")).toEqual({
      event: "token",
      data: "a\nb",
    });
  });

  it("preserves empty data lines (a newline-only token)", () => {
    expect(parseFrame("event: token\ndata: \ndata: ")).toEqual({
      event: "token",
      data: "\n",
    });
  });

  it("ignores comments and frames without data", () => {
    expect(parseFrame(": keep-alive")).toBeNull();
    expect(parseFrame("event: ping")).toBeNull();
  });

  it("handles a data field with no space after the colon", () => {
    expect(parseFrame("data:value")).toEqual({ event: "message", data: "value" });
  });
});

describe("createSseParser", () => {
  it("reassembles newline-only tokens without losing them", () => {
    const { events, parser } = collect();

    parser.push("event: token\ndata: Item one.\n\n");
    parser.push("event: token\ndata: \ndata: \ndata: Item two.\n\n");
    parser.flush();

    expect(events.map((event) => event.data).join("")).toBe("Item one.\n\nItem two.");
  });

  it("handles frames split across network chunks", () => {
    const { events, parser } = collect();
    const payload = "event: token\ndata: hel\n\nevent: token\ndata: lo\n\n";

    for (const character of payload) parser.push(character);

    expect(events.map((event) => event.data).join("")).toBe("hello");
  });

  it("normalises CRLF line endings", () => {
    const { events, parser } = collect();

    parser.push("event: token\r\ndata: a\r\ndata: b\r\n\r\n");

    expect(events).toEqual([{ event: "token", data: "a\nb" }]);
  });

  it("flushes a trailing frame with no blank line", () => {
    const { events, parser } = collect();

    parser.push("event: sources\ndata: []");
    expect(events).toHaveLength(0);

    parser.flush();
    expect(events).toEqual([{ event: "sources", data: "[]" }]);
  });

  it("does nothing when flushing an empty buffer", () => {
    const { events, parser } = collect();
    parser.flush();
    expect(events).toHaveLength(0);
  });
});
