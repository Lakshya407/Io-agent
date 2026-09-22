import { Bot } from "lucide-react";
import { useEffect, useRef } from "react";
import Message, { type ChatMessage } from "./Message";
import MessageInput from "./MessageInput";

interface ChatWindowProps {
  messages: ChatMessage[];
  isWorking: boolean;
  onSend: (text: string) => void;
  onRegenerate: () => void;
  /** Bumping this value focuses the input (e.g. after "New chat"). */
  focusSignal?: number;
}

export default function ChatWindow({
  messages,
  isWorking,
  onSend,
  onRegenerate,
  focusSignal,
}: ChatWindowProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isWorking]);

  // Only the newest assistant reply may be regenerated.
  const lastAssistantId = [...messages]
    .reverse()
    .find((message) => message.role === "assistant")?.id;

  return (
    <main className="chat-window">
      <div className="messages">
        {messages.length === 0 ? (
          <div className="chat-empty">
            <div className="chat-empty-mark" aria-hidden="true">
              <Bot size={22} />
            </div>
            <h2>Ask anything</h2>
            <p>Start a conversation with the agent — your messages appear here.</p>
          </div>
        ) : (
          messages.map((message) => (
            <Message
              key={message.id}
              message={message}
              canRegenerate={
                message.role === "assistant" && message.id === lastAssistantId
              }
              onRegenerate={onRegenerate}
            />
          ))
        )}

        {isWorking && (
          <div className="typing" aria-live="polite">
            <span></span>
            <span></span>
            <span></span>
            Agent is preparing a response
          </div>
        )}

        <div ref={endRef} />
      </div>

      <MessageInput
        onSend={onSend}
        disabled={isWorking}
        focusSignal={focusSignal}
      />
    </main>
  );
}
