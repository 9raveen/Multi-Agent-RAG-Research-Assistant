// ConversationSidebar.jsx
// Lists the logged-in user's past conversations. Clicking one notifies the
// parent (App.jsx) which conversation was selected, so it can fetch full
// history and hand it to ChatPanel. "New Chat" clears the selection so the
// next message starts a fresh conversation instead of continuing one.

import { useState, useEffect } from "react";
import { getConversations } from "../api";

export default function ConversationSidebar({
  activeConversationId,
  onSelect,
  onNewChat,
  refreshKey,
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

    // refreshKey lets the parent force a re-fetch after a new conversation
    // is created by sending the first message of a chat — otherwise a brand
    // new conversation wouldn't appear in this list until manual reload.
    // cancelled guards against setting state if this effect re-runs (new
    // refreshKey) before the previous fetch resolves.
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  return (
    <div className="conversation-sidebar panel">
      <div className="conversation-sidebar-header">
        <h3>Conversations</h3>
        <button type="button" className="new-chat-btn" onClick={onNewChat}>
          + New Chat
        </button>
      </div>

      {loading && <p className="chat-empty-state">Loading...</p>}
      {error && <div className="result-box error">{error}</div>}

      {!loading && !error && conversations.length === 0 && (
        <p className="chat-empty-state">No conversations yet.</p>
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
              {c.title || "Untitled conversation"}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
