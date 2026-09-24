/**
 * Chat history sidebar.
 *
 * Layout: each conversation is a flex row — a shrinking content column (title
 * truncates with an ellipsis) beside a fixed-size delete action. The two are
 * siblings, so a delete click can never select the conversation, and the title
 * can never run under the button.
 */
import { MessageSquarePlus, Search, Trash2 } from "lucide-react";
import { useState, type MouseEvent } from "react";
import { dayGroupLabel, formatRelativeTime } from "../../utils/format";
import type { Conversation } from "../../types/chat";
import UsageIndicator from "./UsageIndicator";
import UserMenu from "./UserMenu";

interface ChatHistoryProps {
  conversations: Conversation[];
  selected: string | null;
  onSelect: (conversationId: string) => void;
  onNew: () => void;
  onDelete: (conversationId: string) => void;
  loading?: boolean;
}

export default function ChatHistory({
  conversations,
  selected,
  onSelect,
  onNew,
  onDelete,
  loading,
}: ChatHistoryProps) {
  const [confirming, setConfirming] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  // Client-side title filter; the backend list is small and this keeps the
  // sidebar responsive while typing.
  const filtered = query.trim()
    ? conversations.filter((conversation) =>
        conversation.title.toLowerCase().includes(query.trim().toLowerCase()),
      )
    : conversations;

  // Group conversations by calendar day (Today / Yesterday / weekday / date).
  const groups = filtered.reduce<Record<string, Conversation[]>>(
    (acc, conversation) => {
      const label = dayGroupLabel(conversation.updated_at);
      (acc[label] ??= []).push(conversation);
      return acc;
    },
    {},
  );
  const groupEntries = Object.entries(groups);

  const confirm = (event: MouseEvent, conversationId: string) => {
    event.stopPropagation();
    setConfirming(conversationId);
  };

  const remove = (event: MouseEvent, conversationId: string) => {
    event.stopPropagation();
    setConfirming(null);
    onDelete(conversationId);
  };

  return (
    <aside className="history" aria-label="Chat history">
      <button className="new-chat" onClick={onNew}>
        <MessageSquarePlus size={16} />
        New chat
      </button>

      <div className="history-search">
        <Search size={14} />
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search chats"
          aria-label="Search conversations"
        />
      </div>

      {loading ? (
        <div className="history-list">
          {[0, 1, 2, 3, 4].map((index) => (
            <div className="history-skeleton" key={index} />
          ))}
        </div>
      ) : groupEntries.length === 0 ? (
        <div className="history-empty">
          {query.trim()
            ? "No conversations match your search."
            : "No conversations yet. Start a new chat."}
        </div>
      ) : (
        <nav className="history-list">
          {groupEntries.map(([label, items]) => (
            <div className="history-group" key={label}>
              <span className="group-label">{label}</span>
              {items.map((conversation) => {
                const isActive = selected === conversation.id;
                if (confirming === conversation.id) {
                  return (
                    <div className="history-item confirming" key={conversation.id}>
                      <span className="history-confirm-text">
                        Delete this conversation?
                      </span>
                      <span className="history-confirm-buttons">
                        <button
                          type="button"
                          className="btn btn-sm btn-secondary"
                          onClick={(event) => {
                            event.stopPropagation();
                            setConfirming(null);
                          }}
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          className="btn btn-sm btn-danger"
                          onClick={(event) =>
                            remove(event, conversation.id)
                          }
                        >
                          Delete
                        </button>
                      </span>
                    </div>
                  );
                }
                return (
                  <div
                    className={`history-item ${isActive ? "selected" : ""}`}
                    key={conversation.id}
                  >
                    <button
                      type="button"
                      className="history-item-content"
                      onClick={() => onSelect(conversation.id)}
                    >
                      <span className="history-item-title">
                        {conversation.title}
                      </span>
                      <span className="history-item-meta">
                        {formatRelativeTime(conversation.updated_at)}
                      </span>
                    </button>
                    <span className="history-item-actions">
                      <button
                        type="button"
                        className="history-delete"
                        onClick={(event) => confirm(event, conversation.id)}
                        aria-label={`Delete conversation ${conversation.title}`}
                        title="Delete conversation"
                      >
                        <Trash2 size={13} />
                      </button>
                    </span>
                  </div>
                );
              })}
            </div>
          ))}
        </nav>
      )}
      <UsageIndicator />
      <UserMenu />
    </aside>
  );
}
