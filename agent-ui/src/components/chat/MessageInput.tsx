import { FileText, Globe, Paperclip, Plus, Send, Square } from "lucide-react";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";

const plusOptions = [
  { label: "Attach file", icon: Paperclip },
  { label: "Add document", icon: FileText },
  { label: "Add context", icon: Globe },
];

interface MessageInputProps {
  onSend: (text: string) => void;
  onStop?: () => void;
  streaming?: boolean;
  disabled: boolean;
  /** Bumping this value focuses the input (e.g. after "New chat"). */
  focusSignal?: number;
}

export default function MessageInput({
  onSend,
  onStop,
  streaming = false,
  disabled,
  focusSignal,
}: MessageInputProps) {
  const [value, setValue] = useState("");
  const [showPlusMenu, setShowPlusMenu] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  // Close the add-menu when clicking elsewhere.
  useEffect(() => {
    const onDocClick = (event: globalThis.MouseEvent) => {
      if (!wrapRef.current?.contains(event.target as Node)) {
        setShowPlusMenu(false);
      }
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  // Focus the input whenever the parent asks for it.
  useEffect(() => {
    textareaRef.current?.focus();
  }, [focusSignal]);

  const send = () => {
    if (value.trim() && !disabled) {
      onSend(value.trim());
      setValue("");
    }
  };

  const keyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      send();
    }
  };

  return (
    <div className="input-wrap" ref={wrapRef}>
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={keyDown}
        placeholder="Ask anything…"
        rows={2}
        aria-label="Message the agent"
      />
      <div className="input-footer">
        <div className="input-left">
          <button
            className="plus-btn"
            type="button"
            aria-label="Add"
            aria-expanded={showPlusMenu}
            aria-haspopup="menu"
            disabled={disabled}
            onClick={() => setShowPlusMenu((open) => !open)}
          >
            <Plus size={16} />
          </button>
          {showPlusMenu && (
            <div className="plus-menu" role="menu">
              <span className="menu-label">Add</span>
              {plusOptions.map((option) => {
                const Icon = option.icon;
                return (
                  <button
                    key={option.label}
                    type="button"
                    className="menu-item"
                    role="menuitem"
                    onClick={() => setShowPlusMenu(false)}
                  >
                    <Icon size={14} />
                    {option.label}
                  </button>
                );
              })}
            </div>
          )}
        </div>
        <button
          className={streaming ? "send stop" : "send"}
          type="button"
          disabled={streaming ? false : !value.trim() || disabled}
          onClick={streaming ? () => onStop?.() : send}
          aria-label={streaming ? "Stop generating" : "Send message"}
        >
          {streaming ? <Square size={15} /> : <Send size={15} />}
        </button>
      </div>
    </div>
  );
}
