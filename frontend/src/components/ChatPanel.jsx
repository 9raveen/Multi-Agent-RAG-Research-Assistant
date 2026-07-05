// components/ChatPanel.jsx
import { useState, useRef, useEffect } from "react";
import { askQuery } from "../api";
import AnswerCard from "./AnswerCard";

export default function ChatPanel({ documentScope }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userText = input;
    setMessages((prev) => [...prev, { role: "user", content: userText }]);
    setInput("");
    setLoading(true);

    try {
      const result = await askQuery(userText, documentScope);
      setMessages((prev) => [...prev, { role: "assistant", result }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", error: err.message },
      ]);
    } finally {
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
          ) : (
            <AnswerCard key={i} result={msg.result} />
          ),
        )}

        {loading && (
          <div className="chat-bubble chat-bubble--loading">Thinking...</div>
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
