import { Bot, Check, Copy, RotateCcw, UserRound } from "lucide-react";
import { useState } from "react";
import Markdown from "./Markdown";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

interface MessageProps {
  message: ChatMessage;
  /** Only the latest assistant reply may be regenerated. */
  canRegenerate?: boolean;
  onRegenerate?: () => void;
}

export default function Message({
  message,
  canRegenerate = false,
  onRegenerate,
}: MessageProps) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard?.writeText(message.content);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable */
    }
  };

  return (
    <article className={`message ${message.role}`}>
      <div className="avatar" aria-hidden="true">
        {message.role === "assistant" ? <Bot size={16} /> : <UserRound size={15} />}
      </div>
      <div className="message-body">
        <div className="message-label">
          {message.role === "assistant" ? "AI Agent" : "You"}
        </div>
        <div className="message-content">
          {message.role === "assistant" ? (
            <Markdown content={message.content} />
          ) : (
            message.content.split("\n").map((line, index) => (
              <p key={index}>{line || "\u00A0"}</p>
            ))
          )}
        </div>
        {message.role === "assistant" && (
          <div className="message-actions">
            <button type="button" onClick={copy} title="Copy response">
              {copied ? <Check size={13} /> : <Copy size={13} />}
              {copied ? "Copied" : "Copy"}
            </button>
            {canRegenerate && (
              <button
                type="button"
                onClick={onRegenerate}
                title="Regenerate response"
              >
                <RotateCcw size={13} />
                Regenerate
              </button>
            )}
          </div>
        )}
      </div>
    </article>
  );
}
