/**
 * Streaming chat state machine.
 *
 * States: idle → sending → streaming → completed | stopped | error.
 * Exactly one AbortController lives at a time; Stop aborts it and the UI
 * never gets stuck in "generating".
 */
import { useCallback, useRef, useState } from "react";
import type { StreamStatus } from "../types/chat";

export function useStreamState() {
  const [status, setStatus] = useState<StreamStatus>("idle");
  const controllerRef = useRef<AbortController | null>(null);

  const begin = useCallback((): AbortSignal => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setStatus("sending");
    return controller.signal;
  }, []);

  const toStreaming = useCallback(() => setStatus("streaming"), []);
  const toCompleted = useCallback(() => {
    controllerRef.current = null;
    setStatus("completed");
  }, []);
  const toStopped = useCallback(() => {
    controllerRef.current = null;
    setStatus("stopped");
  }, []);
  const toError = useCallback(() => {
    controllerRef.current = null;
    setStatus("error");
  }, []);
  const toIdle = useCallback(() => {
    controllerRef.current = null;
    setStatus("idle");
  }, []);

  const stop = useCallback(() => {
    controllerRef.current?.abort();
  }, []);

  const isGenerating = status === "sending" || status === "streaming";

  return {
    status, setStatus, isGenerating,
    begin, stop, toStreaming, toCompleted, toStopped, toError, toIdle,
  };
}
