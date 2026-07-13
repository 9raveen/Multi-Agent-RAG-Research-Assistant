import { useState, useEffect } from "react";
import { getConversations } from "../api";
import ThemeToggle from "./ThemeToggle";

export default function ConversationSidebar({
  activeConversationId,
  onSelect,
  onNewChat,
  refreshKey,
  user,
  onLogout,
  isOpen,
  onToggle,
  onOpenLibrary,
  theme,
  onToggleTheme,
}) {
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadConversations() {
      setLoading(true);
      setError("");
      try {
        const data = await getConversations();
        if (!cancelled) setConversations(data);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadConversations();

    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  if (!isOpen) {
    return (
      <div className="conversation-sidebar conversation-sidebar--closed">
        <button
          className="sidebar-toggle-btn"
          onClick={onToggle}
          title="Open Sidebar"
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            <line x1="9" y1="3" x2="9" y2="21"></line>
          </svg>
        </button>
        <ThemeToggle
          theme={theme}
          onToggle={onToggleTheme}
          className="sidebar-theme-toggle"
        />
      </div>
    );
  }

  return (
    <div className="conversation-sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <img
            src="/logo.png"
            alt="m logo"
            className="custom-logo"
            style={{ height: "20px" }}
          />{" "}
          MARA / AI
        </div>
        <button
          className="sidebar-toggle-btn"
          onClick={onToggle}
          title="Close Sidebar"
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            <line x1="9" y1="3" x2="9" y2="21"></line>
          </svg>
        </button>
      </div>

      <div className="sidebar-actions">
        <button type="button" className="new-chat-btn-dark" onClick={onNewChat}>
          <span
            style={{
              fontSize: "1.2rem",
              marginRight: "0.5rem",
              fontWeight: "300",
            }}
          >
            +
          </span>{" "}
          New research
          <span className="shortcut-hint">⌘N</span>
        </button>
        <button
          type="button"
          className="sidebar-upload-btn"
          onClick={onOpenLibrary}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            style={{ marginRight: "0.5rem" }}
          >
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="12" y1="18" x2="12" y2="12"></line>
            <polyline points="9 15 12 12 15 15"></polyline>
          </svg>
          Upload documents
        </button>
      </div>

      <div className="sidebar-conversations">
        <span className="sidebar-label">CONVERSATIONS</span>
        {loading && (
          <p className="chat-empty-state" style={{ padding: "0 1rem" }}>
            Loading...
          </p>
        )}
        {error && (
          <div className="result-box error" style={{ margin: "0 1rem" }}>
            {error}
          </div>
        )}

        {!loading && !error && conversations.length === 0 && (
          <p className="chat-empty-state" style={{ padding: "0 1rem" }}>
            No conversations yet.
          </p>
        )}

        <ul className="conversation-list">
          {conversations.map((c) => (
            <li key={c.id}>
              <button
                type="button"
                className={
                  "conversation-item" +
                  (c.id === activeConversationId
                    ? " conversation-item--active"
                    : "")
                }
                onClick={() => onSelect(c.id)}
                title={c.title || "Untitled conversation"}
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  style={{
                    marginRight: "0.75rem",
                    flexShrink: 0,
                    opacity: 0.5,
                  }}
                >
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
                <span className="conversation-title-text">
                  {c.title || "New research"}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </div>

      {user && (
        <div className="sidebar-footer">
          <div className="user-info">
            <div className="user-avatar">
              {user.email.charAt(0).toUpperCase()}
            </div>
            <div className="user-details">
              <span className="user-email-text">{user.email}</span>
              <span className="user-status-text">SIGNED IN</span>
            </div>
          </div>
          <ThemeToggle theme={theme} onToggle={onToggleTheme} />
          <button
            type="button"
            className="logout-icon-btn"
            onClick={onLogout}
            title="Log Out"
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
              <polyline points="16 17 21 12 16 7"></polyline>
              <line x1="21" y1="12" x2="9" y2="12"></line>
            </svg>
          </button>
        </div>
      )}
    </div>
  );
}
