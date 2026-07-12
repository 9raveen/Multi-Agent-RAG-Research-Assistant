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
  loadKey,
  onConversationIdChange,
  onMessageSent,
}) {
  const [messages, setMessages] = useState(() =>
    (initialMessages || []).map(dbMessageToLocal),
  );
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  // Reset the visible chat only when the PARENT explicitly loads a
  // different conversation (sidebar click) or starts a new one — signaled
  // by loadKey changing, which App.jsx bumps only in those two cases.
  //
  // Deliberately NOT keyed on conversationId: when this component sends the
  // first message of a brand-new chat, it reports the freshly-created
  // conversation_id back up via onConversationIdChange, which flows back
  // down as a new conversationId prop. If this effect also fired on that
  // change, it would wipe the answer that was just rendered, immediately
  // after receiving it — exactly the "answer appears then chat resets"
  // symptom this fixes.
  useEffect(() => {
    setMessages((initialMessages || []).map(dbMessageToLocal));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadKey]);

  useEffect(() => {
    if (messages.length > 0) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
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
      {documentScope && (
        <p className="chat-scope-banner">Searching within: {documentScope}</p>
      )}

      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="chat-empty-state-full">
            <span className="chat-hero-label">§ NEW RESEARCH SESSION</span>
            <h1 className="chat-hero-title">
              What are we <span className="italic-serif">investigating?</span>
            </h1>
            <p className="chat-hero-desc">
              Ask a question in plain English. MARA's agents will plan, retrieve<br/>
              from your library, and cite as they go.
            </p>

            <div className="chat-input-hero">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="e.g. What are the state-of-the-art methods in multi-agent RAG systems?"
                rows={3}
              />
              <div className="chat-input-hero-footer">
                <div className="chat-shortcuts">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 10l-5 5 5 5"></path><path d="M20 4v7a4 4 0 0 1-4 4H4"></path></svg> TO SEND &middot; 
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{marginLeft: '0.5rem'}}><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg> NEW LINE
                </div>
                <button className="chat-hero-btn" onClick={handleSend} disabled={loading || !input.trim()}>
                  {loading ? "..." : "Begin research"} &rarr;
                </button>
              </div>
            </div>

            <div className="chat-hero-suggestions">
              <button type="button" className="suggestion-card" onClick={() => setInput("Give me a 5-bullet summary of the paper I just uploaded, then list its 3 weakest claims.")}>
                <div className="suggestion-icon">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
                </div>
                <div className="suggestion-text">
                  <h4>Summarise this paper</h4>
                  <p>Give me a 5-bullet summary of the paper I just uploaded, then list its 3 weakest claims.</p>
                </div>
              </button>
              <button type="button" className="suggestion-card" onClick={() => setInput("Compare the methodologies of studies A and B in my library. Which is more rigorous, and why?")}>
                <div className="suggestion-icon">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>
                </div>
                <div className="suggestion-text">
                  <h4>Compare two studies</h4>
                  <p>Compare the methodologies of studies A and B in my library. Which is more rigorous, and why?</p>
                </div>
              </button>
              <button type="button" className="suggestion-card" onClick={() => setInput("Draft a 400-word literature review section on retrieval-augmented generation, citing the...")}>
                <div className="suggestion-icon">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 10v6M2 10l10-5 10 5-10 5z"></path><path d="M6 12v5c3 3 9 3 12 0v-5"></path></svg>
                </div>
                <div className="suggestion-text">
                  <h4>Draft a lit review</h4>
                  <p>Draft a 400-word literature review section on retrieval-augmented generation, citing the...</p>
                </div>
              </button>
              <button type="button" className="suggestion-card" onClick={() => setInput("What's the strongest counter-argument to the main thesis of my most recent upload?")}>
                <div className="suggestion-icon">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path><path d="M13 8H7"></path><path d="M17 12H7"></path></svg>
                </div>
                <div className="suggestion-text">
                  <h4>Find the counter-argument</h4>
                  <p>What's the strongest counter-argument to the main thesis of my most recent upload?</p>
                </div>
              </button>
            </div>
          </div>
        ) : (
          messages.map((msg, i) =>
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
            )
          )
        )}

        <div ref={bottomRef} />
      </div>

      {messages.length > 0 && (
        <div className="chat-input-row">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a follow-up question..."
            rows={2}
          />
          <button onClick={handleSend} disabled={loading}>
            {loading ? "..." : "Send"}
          </button>
        </div>
      )}
    </div>
  );
}
