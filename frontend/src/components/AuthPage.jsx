// AuthPage.jsx
// Combined login/signup screen. This app has no router (App.jsx renders
// everything as one page), so rather than two separately-routed pages this
// is one component that toggles between the two modes — matches how the
// rest of the app is structured, and there's no URL/back-button benefit to
// splitting them here since there's nowhere else to navigate to anyway.

import { useState } from "react";
import { useAuth } from "../context/useAuth";

export default function AuthPage() {
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
      // No further action needed on success — AuthContext's `user` state
      // updates, and App.jsx swaps this screen out for the main app.
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
    <div className="auth-page">
      <div className="auth-card panel">
        <h2>{mode === "login" ? "Log In" : "Create an Account"}</h2>

        <form onSubmit={handleSubmit} className="auth-form">
          <label htmlFor="auth-email">Email</label>
          <input
            id="auth-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            autoComplete="email"
            required
          />

          <label htmlFor="auth-password">Password</label>
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

          {error && <div className="result-box error auth-error">{error}</div>}

          <button type="submit" disabled={submitting}>
            {submitting
              ? mode === "login"
                ? "Logging in..."
                : "Signing up..."
              : mode === "login"
                ? "Log In"
                : "Sign Up"}
          </button>
        </form>

        <p className="auth-toggle">
          {mode === "login"
            ? "Don't have an account?"
            : "Already have an account?"}{" "}
          <button
            type="button"
            className="auth-toggle-btn"
            onClick={toggleMode}
          >
            {mode === "login" ? "Sign up" : "Log in"}
          </button>
        </p>
      </div>
    </div>
  );
}
