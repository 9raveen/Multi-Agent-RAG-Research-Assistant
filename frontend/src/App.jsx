import { useState, useCallback } from "react";
import { useAuth } from "./context/useAuth";
import { getConversation } from "./api";
import CoverPage from "./components/CoverPage";
import AuthPage from "./components/AuthPage";
import UploadPanel from "./components/UploadPanel";
import ChatPanel from "./components/ChatPanel";
import ConversationSidebar from "./components/ConversationSidebar";
import EvaluationDashboard from "./components/EvaluationDashboard";
import "./App.css";

export default function App() {
  const { user, loading, logout } = useAuth();
  const [showAuth, setShowAuth] = useState(false);

  const [lastUploadedFile, setLastUploadedFile] = useState(null);
  const [conversationId, setConversationId] = useState(null);
  const [initialMessages, setInitialMessages] = useState([]);
  const [loadKey, setLoadKey] = useState(0); 
  const [sidebarRefreshKey, setSidebarRefreshKey] = useState(0);
  const [loadingConversation, setLoadingConversation] = useState(false);

  // New UI states
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [rightPanelOpen, setRightPanelOpen] = useState(false);

  const handleSelectConversation = useCallback(async (id) => {
    setLoadingConversation(true);
    try {
      const data = await getConversation(id);
      setConversationId(data.id);
      setInitialMessages(data.messages);
      setLoadKey((k) => k + 1);
    } catch (err) {
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

  if (loading) {
    return (
      <div style={{
        background: '#F4F2EB',
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: "'Inter', sans-serif",
        color: '#7A7A7A',
        fontSize: '1rem',
      }}>
        Loading...
      </div>
    );
  }

  if (!user) {
    if (showAuth) {
      return <AuthPage onBack={() => setShowAuth(false)} />;
    }
    return <CoverPage onEnterWorkspace={() => setShowAuth(true)} />;
  }

  return (
    <div className="app-dashboard">
      <div className="dashboard-layout">
        <ConversationSidebar
          activeConversationId={conversationId}
          onSelect={handleSelectConversation}
          onNewChat={handleNewChat}
          refreshKey={sidebarRefreshKey}
          user={user}
          onLogout={logout}
          isOpen={sidebarOpen}
          onToggle={() => setSidebarOpen(!sidebarOpen)}
          onOpenLibrary={() => setRightPanelOpen(true)}
        />

        <div className="dashboard-main">
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

        {rightPanelOpen && (
          <div className="library-panel">
            <div className="library-header">
              <div>
                <span className="library-label">§ LIBRARY</span>
                <h2 className="library-title">Your documents</h2>
              </div>
              <button className="library-close-btn" onClick={() => setRightPanelOpen(false)}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
              </button>
            </div>

            <UploadPanel onUploadSuccess={(filename) => setLastUploadedFile(filename)} />

            {lastUploadedFile && (
              <div className="indexed-docs">
                <span className="indexed-label">INDEXED (1)</span>
                <div className="indexed-item">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{marginRight: '0.75rem', opacity: 0.5}}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
                  <div className="indexed-item-details">
                    <span className="indexed-item-name">{lastUploadedFile}</span>
                    <span className="indexed-item-meta">Ready &middot; Just now</span>
                  </div>
                </div>
              </div>
            )}

            <div className="library-eval-wrapper">
              <EvaluationDashboard />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
