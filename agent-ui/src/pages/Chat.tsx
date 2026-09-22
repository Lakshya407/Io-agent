/**
 * Chat page (`/chat`).
 *
 * Conversation state model
 * ------------------------
 * `selectedId` is `null` while the user is in a brand-new (unsaved)
 * conversation; its optimistic messages live in `draft`. The moment the server
 * assigns an id, that id is adopted and the conversation's message cache is
 * seeded with the exchange so nothing flashes, then `draft` is cleared.
 *
 * For an existing conversation the React Query cache is the single source of
 * truth: optimistic messages are written into it directly, so a message is
 * never rendered twice (server history + pending buffer).
 *
 * `isNewChat` guards the first-load "select most recent" effect so that
 * clicking *New chat* is not immediately undone.
 */
import { useEffect, useState } from "react";
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
import { useSendMessage } from "../hooks/useChat";
import { useModels } from "../hooks/useModels";
import { queryClient, queryKeys } from "../lib/queryClient";
import { APIError, type PaginatedResponse } from "../types/common";
import type { Message } from "../types/chat";

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
  const sendMutation = useSendMessage();
  const deleteConversation = useDeleteConversation();
  const { toast } = useToast();

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
  const isWorking = sendMutation.isPending || activity.status === "processing";

  const agentState = activity.status === "processing"
    ? "working"
    : activity.status === "completed"
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

  const resetActivity = () => setActivity(emptyActivity());

  const runSend = async (text: string, regenerate = false) => {
    const optimistic: ChatMessage = {
      id: `pending-${Date.now()}`,
      role: "user",
      content: text,
    };
    // Only name a model when the platform actually has one configured.
    const model =
      modelNames.length > 0 && selectedModel !== "Default" ? selectedModel : null;
    const startedAt = performance.now();

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

    // Show the user's message immediately, unless we are only re-running a reply.
    if (!regenerate) {
      if (selectedId === null) {
        setDraft((current) => [...current, optimistic]);
      } else {
        cacheMessages(selectedId, (items) => [...items, toMessage(optimistic)]);
      }
    }

    try {
      const response = await sendMutation.mutateAsync({
        message: text,
        conversation_id: selectedId,
        model,
      });
      const assistant: ChatMessage = {
        id: `assistant-${response.conversation_id}`,
        role: "assistant",
        content: response.message.content,
      };
      const finishedAt = performance.now();

      if (selectedId === null) {
        // Seed the new conversation so adopting its id does not flash an empty
        // chat while the real history is fetched.
        queryClient.setQueryData<PaginatedResponse<Message>>(
          queryKeys.conversationMessages(response.conversation_id),
          {
            items: [toMessage(optimistic), toMessage(assistant)],
            page: 1,
            page_size: 100,
            total: 2,
          },
        );
        setSelectedId(response.conversation_id);
        setIsNewChat(false);
        setDraft([]);
      } else {
        cacheMessages(selectedId, (items) => [...items, toMessage(assistant)]);
      }

      setActivity((previous) => ({
        ...previous,
        status: "completed",
        endedAt: finishedAt,
        model: response.model,
        usage: response.usage,
        toolCalls: previous.toolCalls.map((call) => ({
          ...call,
          status: "completed",
          durationMs: finishedAt - startedAt,
        })),
      }));
    } catch (err) {
      const message =
        err instanceof APIError ? err.message : "Unable to send the message.";
      // Roll the optimistic user message back.
      if (!regenerate) {
        if (selectedId === null) {
          setDraft((current) =>
            current.filter((item) => item.id !== optimistic.id),
          );
        } else {
          cacheMessages(selectedId, (items) =>
            items.filter((item) => item.id !== optimistic.id),
          );
        }
      }
      setActivity((previous) => ({
        ...previous,
        status: "error",
        endedAt: performance.now(),
        error: message,
        toolCalls: previous.toolCalls.map((call) => ({
          ...call,
          status: "failed",
        })),
      }));
      toast(message, "error");
    }
  };

  const newChat = () => {
    setSelectedId(null);
    setIsNewChat(true);
    setDraft([]);
    resetActivity();
    setFocusSignal((current) => current + 1);
  };

  const handleSelect = (conversationId: string) => {
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
      await deleteConversation.mutateAsync(conversationId);
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
            onSend={(text) => void runSend(text)}
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
