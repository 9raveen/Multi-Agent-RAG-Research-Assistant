// AuthContext.jsx
// Tracks the logged-in user app-wide. On mount, checks GET /auth/me to see
// if a valid session cookie already exists (e.g. user refreshed the page) —
// this is how the login persists across reloads without storing anything
// in localStorage ourselves; the httpOnly cookie is the source of truth,
// this context just mirrors what the backend currently says about it.

import { useState, useEffect, useCallback } from "react";
import * as api from "../api";
import { AuthContext } from "./authContextInstance";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true); // true until the initial /auth/me check resolves

  useEffect(() => {
    api
      .getCurrentUser()
      .then((u) => setUser(u))
      .catch(() => setUser(null)) // 401 → just means "not logged in", not an app error
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email, password) => {
    const u = await api.login(email, password);
    setUser(u);
    return u;
  }, []);

  const signup = useCallback(async (email, password) => {
    const u = await api.signup(email, password);
    setUser(u);
    return u;
  }, []);

  const logout = useCallback(async () => {
    await api.logout();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
