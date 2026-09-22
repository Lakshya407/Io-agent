/**
 * Chat + conversation types — mirror `app/schemas/chat.py`.
 */

export type MessageRole = "system" | "user" | "assistant" | "tool";

/** `ChatRequest` — payload for POST /api/v1/chat. */
export interface ChatRequest {
  message: string;
  conversation_id?: string | null;
  model?: string | null;
}

/** `ChatResponseMessage` — the assistant message in a chat response. */
export interface ChatResponseMessage {
  role: MessageRole;
  content: string;
}

/** `TokenUsageSchema` — token accounting for a chat response. */
export interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

/** `ChatResponse` — response for POST /api/v1/chat. */
export interface ChatResponse {
  conversation_id: string;
  message: ChatResponseMessage;
  model: string;
  usage: TokenUsage;
}

/** `ConversationSummary`. */
export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

/** `MessageOut` — a stored message. */
export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  model?: string | null;
  total_tokens?: number;
  created_at: string;
}

/**
 * Message shape used by the existing chat UI components.
 *
 * The backend stores ids as UUID strings; the original demo components used
 * numeric ids. This adapter type keeps the components untouched while the
 * conversion happens in the API layer.
 */
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  /** Present while the assistant reply is still streaming / stopped. */
  streaming?: boolean;
  stopped?: boolean;
}

/** Frontend generation lifecycle for one chat turn. */
export type StreamStatus =
  | "idle"
  | "sending"
  | "streaming"
  | "completed"
  | "stopped"
  | "error";

/** Structured SSE events emitted by `POST /api/v1/chat/stream`. */
export type StreamEvent =
  | { event: "activity"; data: { stage: string; detail?: string; model?: string; provider?: string; duration_ms?: number } }
  | { event: "message_start"; data: { message_id: string; conversation_id: string; model: string; is_new_conversation?: boolean } }
  | { event: "token"; data: { content: string } }
  | { event: "message_complete"; data: { message_id: string; conversation_id: string; model: string; status?: string; usage?: TokenUsage } }
  | { event: "error"; data: { message?: string; code?: string } };
