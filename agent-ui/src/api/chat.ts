/**
 * Chat + conversations API — `POST /chat`, `GET /conversations`,
 * `GET /conversations/{id}/messages`, `DELETE /conversations/{id}`.
 */

import { apiFetch } from "./client";
import type { PaginatedResponse, PageParams } from "../types/common";
import type {
  ChatRequest,
  ChatResponse,
  Conversation,
  Message,
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
