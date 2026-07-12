// api.js
// Centralized calls to the FastAPI backend. Keeps the base URL in one place
// so switching from local dev to a deployed backend later is a one-line change.

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// Every request below sends `credentials: "include"` — this is what makes
// the browser actually attach the httpOnly auth cookie. The backend and
// frontend are on different domains (Vercel vs. HF Spaces / localhost), so
// without this, fetch() silently drops the cookie and every request after
// login looks logged-out even though login itself succeeded.

// ── Auth ─────────────────────────────────────────────────────────────────

async function parseErrorOrThrow(response, fallbackMessage) {
  const errorBody = await response.json().catch(() => ({}));
  throw new Error(errorBody.detail || fallbackMessage);
}

export async function signup(email, password) {
  const response = await fetch(`${API_BASE_URL}/auth/signup`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    await parseErrorOrThrow(response, `Signup failed (${response.status})`);
  }
  return response.json();
}

export async function login(email, password) {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    await parseErrorOrThrow(response, `Login failed (${response.status})`);
  }
  return response.json();
}

export async function logout() {
  const response = await fetch(`${API_BASE_URL}/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) {
    await parseErrorOrThrow(response, `Logout failed (${response.status})`);
  }
}

// Used on app load to check "is there already a valid session?" — throws
// on 401 (not logged in), which callers treat as "no user" rather than a
// real error.
export async function getCurrentUser() {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    method: "GET",
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error("Not authenticated");
  }
  return response.json();
}

// ── Conversations ────────────────────────────────────────────────────────

export async function getConversations() {
  const response = await fetch(`${API_BASE_URL}/conversations`, {
    method: "GET",
    credentials: "include",
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
      credentials: "include",
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
    credentials: "include",
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
    credentials: "include",
    headers: { "Content-Type": "application/json" },
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
    credentials: "include",
    headers: { "Content-Type": "application/json" },
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
