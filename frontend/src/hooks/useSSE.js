import { useCallback, useState } from "react";

import { sendMessage } from "../services/api";

const MARKER = "__SOURCES__";

export const useSSE = () => {
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const reset = useCallback(() => {
    setAnswer("");
    setSources([]);
    setError("");
  }, []);

  const startStream = useCallback(async (question, topK = 5, history = []) => {
    setIsLoading(true);
    setError("");
    setAnswer("");
    setSources([]);

    let sseBuffer = "";
    let sourceBuffer = "";
    let inSources = false;

    const processPayload = (payload) => {
      if (!inSources) {
        const markerIndex = payload.indexOf(MARKER);
        if (markerIndex >= 0) {
          const answerChunk = payload.slice(0, markerIndex);
          if (answerChunk) {
            setAnswer((prev) => prev + answerChunk);
          }
          inSources = true;
          sourceBuffer += payload.slice(markerIndex + MARKER.length);
        } else {
          setAnswer((prev) => prev + payload);
        }
      } else {
        sourceBuffer += payload;
      }
    };

    try {
      const response = await sendMessage(question, topK, history);
      if (!response.ok || !response.body) {
        throw new Error("Failed to connect to chat stream.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        sseBuffer += decoder.decode(value, { stream: true });

        let boundary = sseBuffer.indexOf("\n\n");
        while (boundary !== -1) {
          const frame = sseBuffer.slice(0, boundary);
          sseBuffer = sseBuffer.slice(boundary + 2);

          const payload = frame
            .split("\n")
            .filter((line) => line.startsWith("data:"))
            .map((line) => line.replace(/^data:\s?/, ""))
            .join("\n");

          if (payload) {
            processPayload(payload);
          }

          boundary = sseBuffer.indexOf("\n\n");
        }
      }

      if (sourceBuffer.trim()) {
        setSources(JSON.parse(sourceBuffer));
      }
    } catch (streamError) {
      setError(streamError instanceof Error ? streamError.message : "Streaming failed.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { answer, sources, isLoading, error, reset, startStream };
};
