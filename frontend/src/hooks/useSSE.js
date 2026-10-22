import { useCallback, useEffect, useRef, useState } from "react";

import { SSE_EVENT, createSseParser } from "../lib/sse";
import { readErrorMessage, sendMessage } from "../services/api";

const DEFAULT_TOP_K = 5;

const toMessage = (value, fallback) => {
  if (typeof value === "string" && value.trim()) return value;
  return fallback;
};

export const useSSE = () => {
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const controllerRef = useRef(null);

  const reset = useCallback(() => {
    controllerRef.current?.abort();
    setAnswer("");
    setSources([]);
    setError("");
    setIsLoading(false);
  }, []);

  // Abort an in-flight stream when the component unmounts.
  useEffect(() => () => controllerRef.current?.abort(), []);

  const startStream = useCallback(async (question, topK = DEFAULT_TOP_K, history = []) => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    setIsLoading(true);
    setError("");
    setAnswer("");
    setSources([]);

    let finalAnswer = "";
    let receivedSources = [];
    let streamError = null;

    const parser = createSseParser(({ event, data }) => {
      if (event === SSE_EVENT.TOKEN) {
        finalAnswer += data;
        setAnswer((previous) => previous + data);
        return;
      }
      if (event === SSE_EVENT.SOURCES) {
        try {
          const parsed = JSON.parse(data);
          if (Array.isArray(parsed)) receivedSources = parsed;
        } catch {
          streamError = streamError || "Could not read the source citations.";
        }
        return;
      }
      if (event === SSE_EVENT.ERROR) {
        try {
          streamError = toMessage(JSON.parse(data)?.message, data);
        } catch {
          streamError = toMessage(data, "The answer stream failed.");
        }
      }
    });

    try {
      const response = await sendMessage(question, topK, history, controller.signal);
      if (!response.ok || !response.body) {
        throw new Error(await readErrorMessage(response));
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        parser.push(decoder.decode(value, { stream: true }));
      }
      parser.push(decoder.decode());
      parser.flush();

      if (streamError) {
        setError(streamError);
        return null;
      }

      setSources(receivedSources);
      return finalAnswer;
    } catch (streamFailure) {
      if (streamFailure?.name === "AbortError") return null;
      setError(
        streamFailure instanceof Error
          ? streamFailure.message
          : "Streaming failed. Please try again."
      );
      return null;
    } finally {
      setIsLoading(false);
      if (controllerRef.current === controller) controllerRef.current = null;
    }
  }, []);

  const cancel = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = null;
    setIsLoading(false);
  }, []);

  return { answer, sources, isLoading, error, reset, startStream, cancel };
};
