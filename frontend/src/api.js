// api.js
// Centralized calls to the FastAPI backend.
//
// AUTH APPROACH:
// Bearer token stored in sessionStorage.
//
// Conversation history is NOT sent with query requests.
// The backend uses conversation_id to load the authenticated user's
// conversation history from PostgreSQL.

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const TOKEN_KEY = "auth_token";

// ── Token helpers ─────────────────────────────────────────────────────────

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

  return token
    ? {
        Authorization: `Bearer ${token}`,
      }
    : {};
}

// ── Error handling ────────────────────────────────────────────────────────

async function parseErrorOrThrow(response, fallbackMessage) {
  const errorBody = await response.json().catch(() => ({}));

  throw new Error(errorBody.detail || errorBody.message || fallbackMessage);
}

// ── Authentication ────────────────────────────────────────────────────────

export async function signup(email, password) {
  const response = await fetch(`${API_BASE_URL}/auth/signup`, {
    method: "POST",

    headers: {
      "Content-Type": "application/json",
    },

    body: JSON.stringify({
      email,
      password,
    }),
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

    headers: {
      "Content-Type": "application/json",
    },

    body: JSON.stringify({
      email,
      password,
    }),
  });

  if (!response.ok) {
    await parseErrorOrThrow(response, `Login failed (${response.status})`);
  }

  const data = await response.json();

  setStoredToken(data.access_token);

  return data;
}

export async function createGuestAccount() {
  const response = await fetch(`${API_BASE_URL}/auth/guest`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    await parseErrorOrThrow(
      response,
      `Failed to create demo account (${response.status})`,
    );
  }

  const data = await response.json();

  setStoredToken(data.access_token);

  if (data.is_guest) {
    sessionStorage.setItem("is_guest", "true");
  }

  return data;
}

export async function logout() {
  // Stateless JWT authentication.
  // Clear local auth immediately.

  clearStoredToken();
  sessionStorage.removeItem("is_guest");

  // Best-effort logout request.
  fetch(`${API_BASE_URL}/auth/logout`, {
    method: "POST",
    headers: authHeaders(),
  }).catch(() => {});
}

// ── Current user ─────────────────────────────────────────────────────────

export async function getCurrentUser() {
  if (!getStoredToken()) {
    throw new Error("Not authenticated");
  }

  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    method: "GET",
    headers: authHeaders(),
  });

  if (!response.ok) {
    clearStoredToken();

    throw new Error("Not authenticated");
  }

  return response.json();
}

// ── Conversations ─────────────────────────────────────────────────────────

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

// ── Documents ─────────────────────────────────────────────────────────────

export async function uploadPdf(file) {
  const formData = new FormData();

  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: "POST",

    headers: authHeaders(),

    // Do NOT manually set Content-Type.
    // The browser sets the multipart boundary.

    body: formData,
  });

  if (!response.ok) {
    await parseErrorOrThrow(response, `Upload failed (${response.status})`);
  }

  return response.json();
}

// ── Normal Query ──────────────────────────────────────────────────────────
//
// chatHistory is kept in the function signature temporarily so existing
// components calling askQuery() do not break.
//
// IMPORTANT:
// chatHistory is NOT sent to the backend.
//
// The backend loads previous messages using conversation_id and the
// authenticated user from PostgreSQL.

export async function askQuery(
  query,
  documentScope = null,
  chatHistory = [],
  conversationId = null,
) {
  const response = await fetch(`${API_BASE_URL}/query`, {
    method: "POST",

    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },

    body: JSON.stringify({
      query,
      document_scope: documentScope,
      conversation_id: conversationId,
    }),
  });

  if (!response.ok) {
    await parseErrorOrThrow(response, `Query failed (${response.status})`);
  }

  return response.json();
}

// ── Streaming Query ───────────────────────────────────────────────────────
//
// chatHistory remains in the function signature for compatibility but is
// intentionally NOT sent to the backend.

export async function askQueryStream(
  query,
  documentScope = null,
  chatHistory = [],
  conversationId = null,
  callbacks,
) {
  const { onToken, onRetry, onDone, onError } = callbacks;

  try {
    const response = await fetch(`${API_BASE_URL}/query/stream`, {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
        ...authHeaders(),
      },

      body: JSON.stringify({
        query,
        document_scope: documentScope,
        conversation_id: conversationId,
      }),
    });

    if (!response.ok || !response.body) {
      const errorBody = await response.json().catch(() => ({}));

      onError(
        errorBody.detail ||
          errorBody.message ||
          `Query failed (${response.status})`,
      );

      return;
    }

    const reader = response.body.getReader();

    const decoder = new TextDecoder();

    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();

      if (done) {
        break;
      }

      buffer += decoder.decode(value, {
        stream: true,
      });

      const events = buffer.split("\n\n");

      // Keep incomplete event for the next chunk.
      buffer = events.pop() || "";

      for (const rawEvent of events) {
        let eventType = "message";
        let data = "";

        for (const line of rawEvent.split("\n")) {
          if (line.startsWith("event: ")) {
            eventType = line.slice(7);
          }

          if (line.startsWith("data: ")) {
            data = line.slice(6);
          }
        }

        if (!data) {
          continue;
        }

        let parsed;

        try {
          parsed = JSON.parse(data);
        } catch (error) {
          console.error("Failed to parse streaming event:", data);

          continue;
        }

        if (eventType === "token") {
          onToken?.(parsed.text || "");
        } else if (eventType === "retry") {
          onRetry?.(parsed.revision);
        } else if (eventType === "error") {
          onError?.(
            parsed.message ||
              "An error occurred while generating the response.",
          );
        } else if (eventType === "done") {
          onDone?.(parsed);
        }
      }
    }
  } catch (error) {
    console.error("Streaming query failed:", error);

    onError?.(error.message || "Network error. Please try again.");
  }
}
