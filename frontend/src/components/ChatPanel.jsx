import { useState, useRef, useEffect } from "react";
import { askQueryStream } from "../api";
import AnswerCard from "./AnswerCard";

export default function ChatPanel({ documentScope }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

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
    setInput("");
    setLoading(true);

    const chatHistory = messages.map((msg) => ({
      role: msg.role,
      content: msg.role === "user" ? msg.content : msg.result?.answer || "",
    }));

    setMessages((prev) => [
      ...prev,
      { role: "user", content: userText },
      { role: "assistant", streaming: true, answerText: "" },
    ]);

    try {
      await askQueryStream(userText, documentScope, chatHistory, {
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
