/**
 * Minimal chat header: brand, model selector, live agent status and panel
 * toggles. Kept deliberately sparse — the header must not compete with the
 * conversation. The signed-in user lives in the history sidebar footer.
 */
import { Bot, Check, ChevronDown, PanelLeft, PanelRight } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import AgentStatus, { type AgentState } from "../agent/AgentStatus";
import ThemeToggle from "../ui/ThemeToggle";

interface ChatHeaderProps {
  models: string[];
  selectedModel: string;
  onModelChange: (model: string) => void;
  agentState: AgentState;
  historyOpen: boolean;
  activityOpen: boolean;
  onToggleHistory: () => void;
  onToggleActivity: () => void;
}

export default function ChatHeader({
  models,
  selectedModel,
  onModelChange,
  agentState,
  historyOpen,
  activityOpen,
  onToggleHistory,
  onToggleActivity,
}: ChatHeaderProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const modelOptions = models.length > 0 ? models : ["Default"];

  useEffect(() => {
    if (!menuOpen) return;
    const onDocClick = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [menuOpen]);

  return (
    <header className="chat-header">
      <button
        type="button"
        className={`icon-toggle ${historyOpen ? "on" : ""}`}
        onClick={onToggleHistory}
        aria-label="Toggle chat history"
        aria-pressed={historyOpen}
        title="Chat history"
      >
        <PanelLeft size={17} />
      </button>

      <div className="chat-brand">
        <Bot size={18} />
        <span>AI Agent</span>
      </div>

      <div className="chat-header-spacer" />

      <div className="model-picker" ref={ref}>
        <button
          className="model-btn"
          type="button"
          aria-expanded={menuOpen}
          aria-haspopup="menu"
          onClick={() => setMenuOpen((open) => !open)}
        >
          Model: <span className="model-name">{selectedModel}</span>
          <ChevronDown size={13} />
        </button>
        {menuOpen && (
          <div className="model-menu" role="menu">
            <span className="menu-label">Select model</span>
            {modelOptions.map((model) => (
              <button
                key={model}
                type="button"
                className="menu-item model-item"
                role="menuitem"
                onClick={() => {
                  onModelChange(model);
                  setMenuOpen(false);
                }}
              >
                <Check
                  size={13}
                  className={model === selectedModel ? "tick" : "tick hidden"}
                />
                {model}
              </button>
            ))}
          </div>
        )}
      </div>

      <AgentStatus state={agentState} />

      <ThemeToggle />

      <button
        type="button"
        className={`icon-toggle ${activityOpen ? "on" : ""}`}
        onClick={onToggleActivity}
        aria-label="Toggle agent activity"
        aria-pressed={activityOpen}
        title="Agent activity"
      >
        <PanelRight size={17} />
      </button>
    </header>
  );
}
