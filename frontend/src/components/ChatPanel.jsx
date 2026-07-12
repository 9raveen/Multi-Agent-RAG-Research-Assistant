import { useState, useRef, useEffect } from "react";
import { askQueryStream } from "../api";
import AnswerCard from "./AnswerCard";

// Maps a stored DB message row (from GET /conversations/{id}) into the same
// shape this component already uses internally for rendering, so loading
// history and live-streaming a new answer both render through the same
// AnswerCard path.
function dbMessageToLocal(m) {
  if (m.role === "user") {
    return { role: "user", content: m.content };
  }
  return {
    role: "assistant",
    result: {
      answer: m.content,
      critique_passed: m.critique_passed,
      revisions_taken: m.revisions_taken,
      sources: m.sources || [],
      trace: undefined, // not persisted — only exists for answers generated this session
    },
  };
}

export default function ChatPanel({
  documentScope,
  conversationId,
  initialMessages,
  onConversationIdChange,
  onMessageSent,
}) {
  const [messages, setMessages] = useState(() =>
    (initialMessages || []).map(dbMessageToLocal),
  );
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  // Reset the visible chat whenever a DIFFERENT conversation is selected
  // (sidebar click) or cleared (New Chat) — initialMessages/conversationId
  // change together from the parent, so this re-syncs local state to match.
  useEffect(() => {
    setMessages((initialMessages || []).map(dbMessageToLocal));
  }, [conversationId, initialMessages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const updateLastMessage = (updater) => {
    setMessages((prev) => {
      const updated = [...prev];
      updated[updated.length - 1] = updater(updated[updated.length - 1]);
      return updated;
    });
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userText = input;
    const isNewConversation = !conversationId;
    setInput("");
    setLoading(true);

    setMessages((prev) => [
      ...prev,
      { role: "user", content: userText },
      { role: "assistant", streaming: true, answerText: "" },
    ]);

    try {
      await askQueryStream(userText, documentScope, [], conversationId, {
        onToken: (text) => {
          updateLastMessage((msg) => ({
            ...msg,
            answerText: (msg.answerText || "") + text,
            retrying: false,
          }));
        },
        onRetry: (revision) => {
          updateLastMessage(() => ({
            role: "assistant",
            streaming: true,
            answerText: "",
            retrying: true,
            revision,
          }));
        },
        onDone: (result) => {
          updateLastMessage(() => ({ role: "assistant", result }));
          setLoading(false);
          // First message of a brand new conversation — the backend just
          // created it and returned its id. Tell the parent so follow-up
          // messages continue this same conversation instead of starting
          // a new one each time, and so the sidebar picks it up.
          if (isNewConversation && result.conversation_id) {
            onConversationIdChange?.(result.conversation_id);
          }
          onMessageSent?.();
        },
        onError: (message) => {
          updateLastMessage(() => ({ role: "assistant", error: message }));
          setLoading(false);
        },
      });
    } catch (err) {
      updateLastMessage(() => ({ role: "assistant", error: err.message }));
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-panel">
      <h3>Ask a Question</h3>

      {documentScope && (
        <p className="chat-scope-banner">Searching within: {documentScope}</p>
      )}

      <div className="chat-messages">
        {messages.length === 0 && (
          <p className="chat-empty-state">
            Ask something about your uploaded document.
          </p>
        )}

        {messages.map((msg, i) =>
          msg.role === "user" ? (
            <div key={i} className="chat-bubble chat-bubble--user">
              {msg.content}
            </div>
          ) : msg.error ? (
            <div key={i} className="chat-bubble chat-bubble--error">
              Error: {msg.error}
            </div>
          ) : msg.streaming ? (
            <div key={i} className="chat-bubble chat-bubble--streaming">
              {msg.retrying && (
                <p className="chat-retry-note">
                  Revising answer (attempt {msg.revision})...
                </p>
              )}
              {msg.answerText}
              <span className="streaming-cursor">▍</span>
            </div>
          ) : (
            <AnswerCard key={i} result={msg.result} />
          ),
        )}

        <div ref={bottomRef} />
      </div>

      <div className="chat-input-row">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask something about your uploaded document..."
          rows={2}
        />
        <button onClick={handleSend} disabled={loading}>
          {loading ? "..." : "Send"}
        </button>
      </div>
    </div>
  );
}
