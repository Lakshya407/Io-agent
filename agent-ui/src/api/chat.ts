/**
 * Chat + conversations API — `POST /chat`, `GET /conversations`,
 * `GET /conversations/{id}/messages`, `DELETE /conversations/{id}`.
 */

import { apiFetch, tokenStore } from "./client";
import type { PaginatedResponse, PageParams } from "../types/common";
import type {
  ChatRequest,
  ChatResponse,
  Conversation,
  Message,
  StreamEvent,
} from "../types/chat";

/** LLM responses can take much longer than other endpoints.
 *
 * This must stay >= the backend's OLLAMA_REQUEST_TIMEOUT and the Nginx
 * proxy_read_timeout, otherwise the browser aborts a request the backend is
 * still successfully generating and the user sees a spurious timeout.
 */
const CHAT_TIMEOUT_MS = 180_000;

export const chatApi = {
  /** `POST /api/v1/chat` — send a message and get a reply. */
  send(payload: ChatRequest): Promise<ChatResponse> {
    return apiFetch<ChatResponse>("/chat", {
      method: "POST",
      body: payload,
      timeoutMs: CHAT_TIMEOUT_MS,
    });
  },

  /**
   * `POST /api/v1/chat/stream` — SSE streaming reader.
   *
   * Uses `fetch` + `AbortController` (not `EventSource`, which cannot POST).
   * Calls `onEvent` once per structured SSE frame with JSON data. The
   * caller owns exactly ONE assistant message and appends `token` contents
   * to it. Resolves on `message_complete`, rejects on `error` events or
   * transport failures. `AbortError` propagates so Stop is distinguishable
   * from real failures.
   */
  async stream(
    payload: ChatRequest,
    onEvent: (event: StreamEvent) => void,
    signal: AbortSignal,
  ): Promise<void> {
    const base =
      import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
    const url = `${String(base).replace(/\/+$/, "")}/chat/stream`;
    const token = tokenStore.getAccessToken();
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        "X-Request-ID": crypto.randomUUID(),
      },
      body: JSON.stringify(payload),
      signal,
    });
    if (!response.ok) {
      let message = "Something went wrong while generating the response.";
      let code: string | undefined;
      try {
        const envelope = (await response.json()) as {
          error?: { code?: string; message?: string };
        };
        if (envelope?.error?.message) message = envelope.error.message;
        code = envelope?.error?.code;
      } catch {
        if (response.status === 503)
          message = "AI service is currently unavailable.";
      }
      const error = new Error(message) as Error & { code?: string; status?: number };
      error.code = code;
      error.status = response.status;
      throw error;
    }
    if (!response.body) throw new Error("Streaming is not supported in this browser.");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let pendingEvent: string | null = null;

    const dispatch = (rawEvent: string, rawData: string) => {
      try {
        const data = JSON.parse(rawData) as StreamEvent["data"];
        const event = { event: rawEvent, data } as StreamEvent;
        onEvent(event);
        if (rawEvent === "error") {
          const msg =
            (data as { message?: string }).message ??
            "Something went wrong while generating the response.";
          throw new Error(msg);
        }
      } catch (err) {
        // Re-throw real error events; ignore malformed keep-alive frames.
        if (rawEvent === "error") throw err;
      }
    };

    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";
        for (const frame of frames) {
          let data: string | null = null;
          for (const line of frame.split("\n")) {
            const trimmed = line.trim();
            if (trimmed.startsWith("event:")) {
              pendingEvent = trimmed.slice(6).trim();
            } else if (trimmed.startsWith("data:")) {
              data = trimmed.slice(5).trim();
            }
          }
          if (pendingEvent && data !== null) {
            dispatch(pendingEvent, data);
            pendingEvent = null;
          }
        }
      }
    } finally {
      try {
        reader.releaseLock();
      } catch {
        /* already released on abort */
      }
    }
  },
};

export const conversationsApi = {
  /** `GET /api/v1/conversations` — my conversations. */
  list(params: PageParams = {}): Promise<PaginatedResponse<Conversation>> {
    return apiFetch<PaginatedResponse<Conversation>>("/conversations", {
      params,
    });
  },

  /** `GET /api/v1/conversations/{id}`. */
  get(conversationId: string): Promise<Conversation> {
    return apiFetch<Conversation>(`/conversations/${conversationId}`);
  },

  /** `GET /api/v1/conversations/{id}/messages` — oldest first. */
  messages(
    conversationId: string,
    params: PageParams = {},
  ): Promise<PaginatedResponse<Message>> {
    return apiFetch<PaginatedResponse<Message>>(
      `/conversations/${conversationId}/messages`,
      { params },
    );
  },

  /** `DELETE /api/v1/conversations/{id}` — returns 204. */
  remove(conversationId: string): Promise<void> {
    return apiFetch<void>(`/conversations/${conversationId}`, {
      method: "DELETE",
    });
  },
};
