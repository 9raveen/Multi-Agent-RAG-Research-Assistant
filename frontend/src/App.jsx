import { useState, useCallback } from "react";
import { useAuth } from "./context/useAuth";
import { getConversation } from "./api";
import AuthPage from "./components/AuthPage";
import UploadPanel from "./components/UploadPanel";
import ChatPanel from "./components/ChatPanel";
import ConversationSidebar from "./components/ConversationSidebar";
import EvaluationDashboard from "./components/EvaluationDashboard";
import "./App.css";

export default function App() {
  const { user, loading, logout } = useAuth();

  const [lastUploadedFile, setLastUploadedFile] = useState(null);
  const [conversationId, setConversationId] = useState(null);
  const [initialMessages, setInitialMessages] = useState([]);
  const [loadKey, setLoadKey] = useState(0); // bumped only on explicit sidebar-select / new-chat,
  // NOT when ChatPanel reports a freshly-assigned
  // conversation_id back up (see ChatPanel.jsx)
  const [sidebarRefreshKey, setSidebarRefreshKey] = useState(0);
  const [loadingConversation, setLoadingConversation] = useState(false);

  const handleSelectConversation = useCallback(async (id) => {
    setLoadingConversation(true);
    try {
      const data = await getConversation(id);
      setConversationId(data.id);
      setInitialMessages(data.messages);
      setLoadKey((k) => k + 1);
    } catch (err) {
      // Conversation might belong to another session, or simply no longer
      // exist — fall back to a clean new-chat state rather than leaving the
      // UI stuck on a broken selection.
      console.error("Failed to load conversation:", err.message);
      setConversationId(null);
      setInitialMessages([]);
      setLoadKey((k) => k + 1);
    } finally {
      setLoadingConversation(false);
    }
  }, []);

  const handleNewChat = useCallback(() => {
    setConversationId(null);
    setInitialMessages([]);
    setLoadKey((k) => k + 1);
  }, []);

  const handleConversationIdChange = useCallback((newId) => {
    setConversationId(newId);
  }, []);

  const handleMessageSent = useCallback(() => {
    setSidebarRefreshKey((k) => k + 1);
  }, []);

  // Still resolving the initial "is there already a session?" check — avoid
  // flashing the login screen for users who are actually already logged in.
  if (loading) {
    return (
      <div className="app">
        <p className="chat-empty-state">Loading...</p>
      </div>
    );
  }

  if (!user) {
    return <AuthPage />;
  }

  return (
    <div className="app">
      <header>
        <h1>Multi-Agent RAG Research Assistant</h1>
        <p>LangGraph · Qdrant · Groq · FastAPI</p>
        <div className="user-bar">
          <span className="user-email">{user.email}</span>
          <button type="button" className="logout-btn" onClick={logout}>
            Log Out
          </button>
        </div>
      </header>
      <main>
        <UploadPanel
          onUploadSuccess={(filename) => setLastUploadedFile(filename)}
        />

        <div className="chat-layout">
          <ConversationSidebar
            activeConversationId={conversationId}
            onSelect={handleSelectConversation}
            onNewChat={handleNewChat}
            refreshKey={sidebarRefreshKey}
          />

          {loadingConversation ? (
            <div className="chat-panel">
              <p className="chat-empty-state">Loading conversation...</p>
            </div>
          ) : (
            <ChatPanel
              documentScope={lastUploadedFile}
              conversationId={conversationId}
              initialMessages={initialMessages}
              loadKey={loadKey}
              onConversationIdChange={handleConversationIdChange}
              onMessageSent={handleMessageSent}
            />
          )}
        </div>

        <EvaluationDashboard />
      </main>
    </div>
  );
}
