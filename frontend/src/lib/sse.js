/**
 * Minimal, dependency-free Server-Sent Events parser.
 *
 * Every physical line of a payload arrives as its own `data:` field, so lines
 * are rejoined with "\n". This is what preserves markdown newlines: a token
 * that is just "\n" arrives as `data: ` + `data: ` and is reassembled intact.
 */

export const SSE_EVENT = {
  TOKEN: "token",
  SOURCES: "sources",
  ERROR: "error",
};

/**
 * Parse a single SSE frame into an event.
 * @param {string} frame Raw frame text without the trailing blank line.
 * @returns {{event: string, data: string} | null}
 */
export function parseFrame(frame) {
  let event = "message";
  const dataLines = [];

  for (const line of frame.split("\n")) {
    if (!line || line.startsWith(":")) continue;

    const separator = line.indexOf(":");
    const field = separator === -1 ? line : line.slice(0, separator);
    let value = separator === -1 ? "" : line.slice(separator + 1);
    if (value.startsWith(" ")) value = value.slice(1);

    if (field === "event") event = value;
    else if (field === "data") dataLines.push(value);
  }

  if (dataLines.length === 0) return null;
  return { event, data: dataLines.join("\n") };
}

/**
 * Create a stateful parser for a streaming response body.
 * @param {(event: {event: string, data: string}) => void} onEvent
 */
export function createSseParser(onEvent) {
  let buffer = "";

  const drain = () => {
    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const frame = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const parsed = parseFrame(frame);
      if (parsed) onEvent(parsed);
      boundary = buffer.indexOf("\n\n");
    }
  };

  return {
    /** Feed decoded text from the network. */
    push(text) {
      if (!text) return;
      buffer += text.replace(/\r\n?/g, "\n");
      drain();
    },
    /** Flush a trailing frame that arrived without a final blank line. */
    flush() {
      if (buffer.trim()) {
        const parsed = parseFrame(buffer);
        buffer = "";
        if (parsed) onEvent(parsed);
      }
    },
    /** Currently buffered, not-yet-complete text. */
    get pending() {
      return buffer;
    },
  };
}

export default createSseParser;
