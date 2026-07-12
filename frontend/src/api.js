// api.js
// Centralized calls to the FastAPI backend.
//
// AUTH APPROACH: Bearer token in the Authorization header, stored in
// sessionStorage — not an httpOnly cookie. This is a deliberate deployment-
// specific choice: Hugging Face Spaces' proxy has an active bug that drops
// the Access-Control-Allow-Credentials header on CORS preflight requests,
// which breaks cookie-based cross-origin auth (Vercel frontend → HF Spaces
// backend) no matter how correctly the backend's CORS config is set up. A
// bearer token never triggers that credentialed-request preflight check in
// the first place, so this sidesteps the platform bug entirely.
//
// sessionStorage (not localStorage): clears when the tab closes rather than
// persisting indefinitely — a reasonable middle ground for a portfolio
// project. Trade-off vs. the original httpOnly cookie approach: a token in
// sessionStorage is readable by any JS running on the page, so it's
// somewhat more exposed to XSS than an httpOnly cookie would be. Acceptable
// here since this app has no third-party scripts.

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const TOKEN_KEY = "auth_token";

export function getStoredToken() {
  return sessionStorage.getItem(TOKEN_KEY);
}

function setStoredToken(token) {
  sessionStorage.setItem(TOKEN_KEY, token);
}

function clearStoredToken() {
  sessionStorage.removeItem(TOKEN_KEY);
}

function authHeaders() {
  const token = getStoredToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ── Auth ─────────────────────────────────────────────────────────────────

async function parseErrorOrThrow(response, fallbackMessage) {
  const errorBody = await response.json().catch(() => ({}));
  throw new Error(errorBody.detail || fallbackMessage);
}

export async function signup(email, password) {
  const response = await fetch(`${API_BASE_URL}/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    await parseErrorOrThrow(response, `Signup failed (${response.status})`);
  }
  const data = await response.json();
  setStoredToken(data.access_token);
  return data;
}

export async function login(email, password) {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    await parseErrorOrThrow(response, `Login failed (${response.status})`);
  }
  const data = await response.json();
  setStoredToken(data.access_token);
  return data;
}

export async function logout() {
  // Stateless JWT — nothing meaningful to await server-side. Clear the
  // local token immediately; fire the endpoint best-effort for API symmetry.
  clearStoredToken();
  fetch(`${API_BASE_URL}/auth/logout`, {
    method: "POST",
    headers: authHeaders(),
  }).catch(() => {});
}

// Used on app load to check "is there already a valid session?" — if no
// token is stored, skip the network call entirely and just report
// not-authenticated. Throws on 401 (expired/invalid token), which callers
// treat as "no user" rather than a real error.
export async function getCurrentUser() {
  if (!getStoredToken()) {
    throw new Error("Not authenticated");
  }
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    method: "GET",
    headers: authHeaders(),
  });
  if (!response.ok) {
    clearStoredToken(); // stored token is expired/invalid — drop it so we don't keep retrying with it
    throw new Error("Not authenticated");
  }
  return response.json();
}

// ── Conversations ────────────────────────────────────────────────────────

export async function getConversations() {
  const response = await fetch(`${API_BASE_URL}/conversations`, {
    method: "GET",
    headers: authHeaders(),
  });
  if (!response.ok) {
    await parseErrorOrThrow(
      response,
      `Failed to load conversations (${response.status})`,
    );
  }
  return response.json();
}

export async function getConversation(conversationId) {
  const response = await fetch(
    `${API_BASE_URL}/conversations/${conversationId}`,
    {
      method: "GET",
      headers: authHeaders(),
    },
  );
  if (!response.ok) {
    await parseErrorOrThrow(
      response,
      `Failed to load conversation (${response.status})`,
    );
  }
  return response.json();
}

// ── Documents / Query ───────────────────────────────────────────────────

export async function uploadPdf(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: "POST",
    headers: authHeaders(), // no Content-Type here — browser sets the multipart
    // boundary itself; setting it manually breaks the upload
    body: formData,
  });

  if (!response.ok) {
    await parseErrorOrThrow(response, `Upload failed (${response.status})`);
  }

  return response.json();
}

// conversationId: pass null/undefined to start a new conversation; pass an
// existing id to continue one. chat_history is still sent for backward
// compatibility with older backend versions, but as of Phase 8 the backend
// ignores it and loads history from Postgres itself using conversationId.
export async function askQuery(
  query,
  documentScope = null,
  chatHistory = [],
  conversationId = null,
) {
  const response = await fetch(`${API_BASE_URL}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      query,
      document_scope: documentScope,
      chat_history: chatHistory,
      conversation_id: conversationId,
    }),
  });

  if (!response.ok) {
    await parseErrorOrThrow(response, `Query failed (${response.status})`);
  }

  return response.json();
}

export async function askQueryStream(
  query,
  documentScope,
  chatHistory,
  conversationId,
  callbacks,
) {
  const { onToken, onRetry, onDone, onError } = callbacks;

  const response = await fetch(`${API_BASE_URL}/query/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      query,
      document_scope: documentScope,
      chat_history: chatHistory,
      conversation_id: conversationId,
    }),
  });

  if (!response.ok || !response.body) {
    const errorBody = await response.json().catch(() => ({}));
    onError(errorBody.detail || `Query failed (${response.status})`);
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const events = buffer.split("\n\n");
    buffer = events.pop(); // last chunk may be incomplete — keep it for next read

    for (const rawEvent of events) {
      let eventType = "message";
      let data = "";
      for (const line of rawEvent.split("\n")) {
        if (line.startsWith("event: ")) eventType = line.slice(7);
        if (line.startsWith("data: ")) data = line.slice(6);
      }
      if (!data) continue;
      const parsed = JSON.parse(data);

      if (eventType === "token") onToken(parsed.text);
      else if (eventType === "retry") onRetry(parsed.revision);
      else if (eventType === "error") onError(parsed.message);
      else if (eventType === "done") onDone(parsed); // includes conversation_id now
    }
  }
}
