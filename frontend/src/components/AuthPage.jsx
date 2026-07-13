// AuthPage.jsx
// Combined login/signup screen. This app has no router (App.jsx renders
// everything as one page), so rather than two separately-routed pages this
// is one component that toggles between the two modes — matches how the
// rest of the app is structured, and there's no URL/back-button benefit to
// splitting them here since there's nowhere else to navigate to anyway.

import { useState } from "react";
import { useAuth } from "../context/useAuth";
import ThemeToggle from "./ThemeToggle";
import "./AuthPage.css";

export default function AuthPage({ onBack, theme, onToggleTheme }) {
  const { login, signup } = useAuth();
  const [mode, setMode] = useState("login"); // "login" | "signup"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) return;

    setSubmitting(true);
    setError("");

    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await signup(email, password);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const toggleMode = () => {
    setMode((m) => (m === "login" ? "signup" : "login"));
    setError("");
  };

  return (
    <div className="auth-split-page">
      <div className="auth-left">
        <div className="auth-left-top">
          {onBack && (
            <button type="button" onClick={onBack} className="back-link">
              &larr; BACK TO COVER
            </button>
          )}
          <ThemeToggle theme={theme} onToggle={onToggleTheme} />
        </div>
        <div className="auth-left-content">
          <span className="library-card-label">THE LIBRARY CARD</span>
          <h1 className="auth-heading">
            Welcome to <span className="italic-serif">MARA</span>.
          </h1>
          <p className="auth-desc">
            A quiet reading room where multiple research agents work on your
            questions. Sign in to open your workspace.
          </p>
        </div>
        <div className="auth-left-footer">
          <span>VOL. 01</span>
          <span>EST. MMXXIV</span>
        </div>
      </div>

      <div className="auth-right">
        <div className="auth-form-container">
          <div className="auth-logo">
            <img
              src="/logo.png"
              alt="m logo"
              className="custom-logo"
              style={{ height: "24px" }}
            />{" "}
            MARA / AI
          </div>

          <h2 className="auth-title">
            {mode === "login" ? "Sign in" : "Create account"}
          </h2>
          <p className="auth-subtitle">
            {mode === "login"
              ? "Continue to your research library."
              : "Start your research library."}
          </p>

          <form onSubmit={handleSubmit} className="auth-form-styled">
            <div className="input-group">
              <label htmlFor="auth-email">EMAIL</label>
              <input
                id="auth-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@library.com"
                autoComplete="email"
                required
              />
            </div>

            <div className="input-group">
              <label htmlFor="auth-password">PASSWORD</label>
              <input
                id="auth-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete={
                  mode === "login" ? "current-password" : "new-password"
                }
                required
              />
            </div>

            {error && (
              <div className="result-box error auth-error">{error}</div>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="auth-submit-btn"
            >
              {submitting
                ? mode === "login"
                  ? "Signing in..."
                  : "Creating..."
                : mode === "login"
                  ? "Sign in"
                  : "Create account"}
            </button>
          </form>

          <p className="auth-toggle-text">
            {mode === "login" ? "New to MARA? " : "Already have an account? "}
            <button
              type="button"
              className="auth-toggle-inline"
              onClick={toggleMode}
            >
              {mode === "login" ? "Create one" : "Sign in"}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
