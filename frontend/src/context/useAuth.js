// useAuth.js
// Kept in its own file, separate from AuthContext.jsx — a file that exports
// both a component (AuthProvider) and a hook breaks Vite's Fast Refresh
// (eslint's react-refresh/only-export-components rule catches this).

import { useContext } from "react";
import { AuthContext } from "./authContextInstance";

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
