/**
 * Chat page (`/chat`) — real-time SSE streaming.
 *
 * Conversation state model
 * ------------------------
 * `selectedId` is `null` while the user is in a brand-new (unsaved)
 * conversation; its optimistic messages live in `draft`. The moment the
 * stream emits `message_start`/`message_complete`, that id is adopted and the
 * conversation's message cache is seeded so nothing flashes, then `draft` is
 * cleared.
 *
 * Streaming model: exactly ONE assistant placeholder is created per turn and
 * every `token` event appends to it (`content += chunk`). Stop aborts the
 * fetch via AbortController; the partial reply stays visible and persists
 * server-side with `status="stopped"`.
 *
 * `isNewChat` guards the first-load "select most recent" effect so that
 * clicking *New chat* is not immediately undone.
 */
import { useEffect, useRef, useState } from "react";
import ActivityPanel, {
  emptyActivity,
  type ActivityState,
} from "../components/agent/ActivityPanel";
import ChatHeader from "../components/chat/ChatHeader";
import ChatHistory from "../components/chat/ChatHistory";
import ChatWindow from "../components/chat/ChatWindow";
import type { ChatMessage } from "../components/chat/Message";
import { useToast } from "../context/ToastContext";
import {
  useConversationMessages,
  useConversations,
  useDeleteConversation,
} from "../hooks/useConversations";
import { useStreamState } from "../hooks/useChatStream";
import { useModels } from "../hooks/useModels";
import { chatApi } from "../api/chat";
import { queryClient, queryKeys } from "../lib/queryClient";
import { APIError, type PaginatedResponse } from "../types/common";
import type { Message, StreamEvent } from "../types/chat";

type MessagesUpdater = (items: Message[]) => Message[];

/** Remove the trailing assistant message (used when regenerating a reply). */
function dropLastAssistant<T extends { role: string }>(items: T[]): T[] {
  const lastIndex = [...items]
    .reverse()
    .findIndex((item) => item.role === "assistant");
  if (lastIndex === -1) return items;
  const index = items.length - 1 - lastIndex;
  return items.filter((_, itemIndex) => itemIndex !== index);
}

function friendlyStreamError(err: unknown): string {
  if (err instanceof DOMException && err.name === "AbortError") {
    return "Generation was stopped.";
  }
  if (err instanceof Error && err.message) {
    const msg = err.message;
    if (/unavailable/i.test(msg)) return "AI service is currently unavailable.";
    if (/not available/i.test(msg)) return "Selected model is unavailable.";
    return msg;
  }
  if (err instanceof APIError) return err.message;
  return "Something went wrong while generating the response.";
}

export default function Chat() {
  const { data: conversationsData, isLoading: conversationsLoading } =
    useConversations();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  /**
   * True only when the user explicitly chose "New chat". Without this flag the
   * first-load effect below would re-select the most recent conversation and
   * silently cancel the new one — the original "new chat does nothing" bug.
   */
  const [isNewChat, setIsNewChat] = useState(false);
  /** Optimistic messages for a conversation that has no server id yet. */
  const [draft, setDraft] = useState<ChatMessage[]>([]);
  const [historyOpen, setHistoryOpen] = useState(
    typeof window === "undefined" || window.innerWidth > 900,
  );
  const [activityOpen, setActivityOpen] = useState(
    typeof window === "undefined" || window.innerWidth > 900,
  );
  const [activity, setActivity] = useState<ActivityState>(emptyActivity());
  const [focusSignal, setFocusSignal] = useState(0);

  const { data: messagesData } = useConversationMessages(selectedId);
  const { data: modelsData } = useModels({ activeOnly: true });
  const deleteConversation = useDeleteConversation();
  const { toast } = useToast();
  const stream = useStreamState();
  // The conversation id assigned by `message_start` for this turn (new chats).
  const streamConvRef = useRef<string | null>(null);

  const modelNames = (modelsData?.items ?? [])
    .filter((model) => model.is_active)
    .map((model) => model.name);
  const [selectedModel, setSelectedModel] = useState("Default");

  const historyMessages: ChatMessage[] = (messagesData?.items ?? [])
    .filter((message) => message.role === "user" || message.role === "assistant")
    .map((message) => ({
      id: message.id,
      role: message.role as "user" | "assistant",
      content: message.content,
    }));

  // A new conversation renders its draft; every other conversation renders its
  // server cache (which optimistic updates also write to). One source of truth
  // → no duplicated messages.
  const messages = selectedId === null ? draft : historyMessages;
  const isGenerating = stream.isGenerating;
  const isWorking = isGenerating || activity.status === "processing";

  const agentState = activity.status === "processing"
    ? "working"
    : activity.status === "completed" || activity.status === "stopped"
      ? "completed"
      : activity.status === "error"
        ? "error"
        : "online";

  // Pick up the most recent conversation on first load — never when the user
  // has asked for a new one.
  useEffect(() => {
    if (
      selectedId === null &&
      !isNewChat &&
      conversationsData &&
      conversationsData.items.length > 0
    ) {
      setSelectedId(conversationsData.items[0].id);
    }
  }, [conversationsData, selectedId, isNewChat]);

  /** Write optimistically into a conversation's cached message page. */
  const cacheMessages = (conversationId: string, updater: MessagesUpdater) => {
    queryClient.setQueryData<PaginatedResponse<Message>>(
      queryKeys.conversationMessages(conversationId),
      (current) => {
        if (!current) return current;
        return { ...current, items: updater(current.items) };
      },
    );
  };

  const toMessage = (message: ChatMessage): Message => ({
    id: message.id,
    role: message.role,
    content: message.content,
    model: null,
    total_tokens: 0,
    created_at: new Date().toISOString(),
  });

  const resetActivity = () => {
    setActivity(emptyActivity());
    stream.toIdle();
  };

  /** Append streamed text to the single assistant placeholder. */
  const appendToken = (placeholderId: string, chunk: string) => {
    if (selectedId === null) {
      setDraft((current) =>
        current.map((m) =>
          m.id === placeholderId ? { ...m, content: m.content + chunk } : m,
        ),
      );
    } else {
      cacheMessages(selectedId, (items) =>
        items.map((m) =>
          m.id === placeholderId
            ? { ...m, content: m.content + chunk }
            : m,
        ),
      );
    }
  };

  const finalizePlaceholder = (
    placeholderId: string,
    opts: { stopped?: boolean } = {},
  ) => {
    if (selectedId === null) {
      setDraft((current) =>
        current.map((m) =>
          m.id === placeholderId
            ? { ...m, streaming: false, stopped: opts.stopped }
            : m,
        ),
      );
    }
    // Server-cached messages (backend `Message`) carry no streaming flag —
    // the placeholder simply stops being updated; a refetch reconciles ids.
  };

  const runSend = async (text: string, regenerate = false) => {
    if (stream.isGenerating) return;
    const optimistic: ChatMessage = {
      id: `pending-${Date.now()}`,
      role: "user",
      content: text,
    };
    const placeholderId = `streaming-${Date.now()}`;
    const placeholder: ChatMessage = {
      id: placeholderId,
      role: "assistant",
      content: "",
      streaming: true,
    };
    // Only name a model when the platform actually has one configured.
    const model =
      modelNames.length > 0 && selectedModel !== "Default" ? selectedModel : null;
    const startedAt = performance.now();
    streamConvRef.current = selectedId;
    const signal = stream.begin();

    setActivity({
      status: "processing",
      startedAt,
      model: model ?? undefined,
      toolCalls: [
        {
          id: `call-${Date.now()}`,
          name: "Model call",
          detail: model ?? "Default model",
          status: "running",
        },
      ],
    });

    // Show the user's message + an empty assistant placeholder immediately.
    if (!regenerate) {
      if (selectedId === null) {
        setDraft((current) => [...current, optimistic, placeholder]);
      } else {
        cacheMessages(selectedId, (items) => [
          ...items,
          toMessage(optimistic),
          { ...toMessage(placeholder), id: placeholderId },
        ]);
      }
    } else if (selectedId === null) {
      setDraft((current) => [...current, placeholder]);
    } else {
      cacheMessages(selectedId, (items) => [
        ...items,
        { ...toMessage(placeholder), id: placeholderId },
      ]);
    }

    const onEvent = (event: StreamEvent) => {
      if (event.event === "activity") {
        const { stage, detail, model: m } = event.data;
        setActivity((prev) => ({
          ...prev,
          status: "processing",
          model: m ?? prev.model,
          toolCalls: prev.toolCalls.map((call) => ({
            ...call,
            detail: detail ?? call.detail,
            status: "running" as const,
          })),
        }));
      } else if (event.event === "message_start") {
        stream.toStreaming();
        streamConvRef.current = event.data.conversation_id;
        if (event.data.model) {
          setActivity((prev) => ({ ...prev, model: event.data.model }));
        }
      } else if (event.event === "token") {
        appendToken(placeholderId, event.data.content);
      }
    };

    try {
      let completedConv: string | null = null;
      let completedModel: string | null = null;
      let completedUsage: Message["total_tokens"] extends never
        ? never
        : { prompt_tokens: number; completion_tokens: number; total_tokens: number } | undefined;

      await chatApi.stream(
        { message: text, conversation_id: selectedId, model },
        (event) => {
          onEvent(event);
          if (event.event === "message_complete") {
            completedConv = event.data.conversation_id;
            completedModel = event.data.model;
            completedUsage = event.data.usage;
          }
        },
        signal,
      );

      const finishedAt = performance.now();
      finalizePlaceholder(placeholderId);
      stream.toCompleted();

      if (selectedId === null && completedConv) {
        // Seed the new conversation so adopting its id does not flash empty.
        setDraft((current) => {
          const userMsg = current.find((m) => m.id === optimistic.id) ?? optimistic;
          const asstMsg = current.find((m) => m.id === placeholderId) ?? placeholder;
          queryClient.setQueryData<PaginatedResponse<Message>>(
            queryKeys.conversationMessages(completedConv as string),
            {
              items: [toMessage({ ...userMsg, id: userMsg.id }), toMessage({ ...asstMsg, id: `assistant-${completedConv}` })],
              page: 1,
              page_size: 100,
              total: 2,
            },
          );
          return [];
        });
        setSelectedId(completedConv);
        setIsNewChat(false);
      } else {
        // Re-key the placeholder to the server message id on refresh safety.
        queryClient.invalidateQueries({
          queryKey: queryKeys.conversationMessages(
            (completedConv as string | null) ?? selectedId ?? "none",
          ),
        });
      }
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      // Keep the usage indicator/allowance in sync after the turn completes.
      queryClient.invalidateQueries({ queryKey: ["usage"] });

      setActivity((previous) => ({
        ...previous,
        status: "completed",
        endedAt: finishedAt,
        model: completedModel ?? previous.model,
        usage: (completedUsage as ActivityState["usage"]) ?? previous.usage,
        toolCalls: previous.toolCalls.map((call) => ({
          ...call,
          status: "completed",
          durationMs: finishedAt - startedAt,
        })),
      }));
    } catch (err) {
      const aborted =
        err instanceof DOMException && err.name === "AbortError";
      const finishedAt = performance.now();
      if (aborted) {
        // Stop: keep the partial reply, mark it stopped.
        finalizePlaceholder(placeholderId, { stopped: true });
        stream.toStopped();
        if (selectedId === null && streamConvRef.current) {
          // Adopt the id so the partial reply persists across refresh.
          const conv = streamConvRef.current;
          setDraft((current) => {
            const items = current.filter((m) => m.id !== placeholderId || m.content);
            if (items.length === 0) return current;
            queryClient.setQueryData<PaginatedResponse<Message>>(
              queryKeys.conversationMessages(conv),
              {
                items: items.map((m) => toMessage(m)),
                page: 1,
                page_size: 100,
                total: items.length,
              },
            );
            return [];
          });
          setSelectedId(conv);
          setIsNewChat(false);
        } else {
          queryClient.invalidateQueries({ queryKey: ["conversations"] });
        }
        setActivity((previous) => ({
          ...previous,
          status: "stopped",
          endedAt: finishedAt,
          error: "Generation was stopped.",
          toolCalls: previous.toolCalls.map((call) => ({
            ...call,
            status: "completed",
            durationMs: finishedAt - startedAt,
          })),
        }));
      } else {
        const message = friendlyStreamError(err);
        finalizePlaceholder(placeholderId);
        stream.toError();
        setActivity((previous) => ({
          ...previous,
          status: "error",
          endedAt: finishedAt,
          error: message,
          toolCalls: previous.toolCalls.map((call) => ({
            ...call,
            status: "failed",
          })),
        }));
        toast(message, "error");
      }
    }
  };

  const handleStop = () => {
    stream.stop();
  };

  const newChat = () => {
    if (stream.isGenerating) stream.stop();
    setSelectedId(null);
    setIsNewChat(true);
    setDraft([]);
    resetActivity();
    setFocusSignal((current) => current + 1);
  };

  const handleSelect = (conversationId: string) => {
    if (stream.isGenerating) return;
    setSelectedId(conversationId);
    setIsNewChat(false);
    setDraft([]);
    resetActivity();
  };

  const regenerate = () => {
    if (isWorking) return;
    const lastUser = [...messages].reverse().find((m) => m.role === "user");
    if (!lastUser) return;

    if (selectedId === null) {
      setDraft((current) => dropLastAssistant(current));
    } else {
      cacheMessages(selectedId, dropLastAssistant);
    }
    void runSend(lastUser.content, true);
  };

  const handleDelete = async (conversationId: string) => {
    try {
      const { conversationsApi } = await import("../api/chat");
      await conversationsApi.remove(conversationId);
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      // Deleting the open conversation returns to a fresh new chat.
      if (selectedId === conversationId) {
        setSelectedId(null);
        setIsNewChat(true);
        setDraft([]);
        resetActivity();
        setFocusSignal((current) => current + 1);
      }
      toast("Conversation deleted.", "success");
    } catch (err) {
      toast(
        err instanceof APIError
          ? err.message
          : "Unable to delete the conversation.",
        "error",
      );
    }
  };

  const bodyClassName = [
    "workspace-body",
    historyOpen ? "" : "hist-closed",
    activityOpen ? "" : "act-closed",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className="app-shell">
      <div className="workspace">
        <ChatHeader
          models={modelNames}
          selectedModel={selectedModel}
          onModelChange={setSelectedModel}
          agentState={agentState}
          historyOpen={historyOpen}
          activityOpen={activityOpen}
          onToggleHistory={() => setHistoryOpen((open) => !open)}
          onToggleActivity={() => setActivityOpen((open) => !open)}
        />
        <div className={bodyClassName}>
          <ChatHistory
            conversations={conversationsData?.items ?? []}
            selected={selectedId}
            onSelect={handleSelect}
            onNew={newChat}
            onDelete={handleDelete}
            loading={conversationsLoading}
          />
          <ChatWindow
            messages={messages}
            isWorking={isWorking}
            streaming={isGenerating}
            onSend={(text) => void runSend(text)}
            onStop={handleStop}
            onRegenerate={regenerate}
            focusSignal={focusSignal}
          />
          <ActivityPanel
            activity={activity}
            onClose={() => setActivityOpen(false)}
          />
        </div>
        {(historyOpen || activityOpen) && (
          <div
            className="panel-backdrop"
            aria-hidden="true"
            onClick={() => {
              setHistoryOpen(false);
              setActivityOpen(false);
            }}
          />
        )}
      </div>
    </div>
  );
}
