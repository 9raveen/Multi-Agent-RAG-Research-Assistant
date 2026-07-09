// api.js
// Centralized calls to the FastAPI backend. Keeps the base URL in one place
// so switching from local dev to a deployed backend later is a one-line change.

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function uploadPdf(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Upload failed (${response.status})`);
  }

  return response.json();
}

export async function askQuery(query, documentScope = null, chatHistory = []) {
  const response = await fetch(`${API_BASE_URL}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      document_scope: documentScope,
      chat_history: chatHistory,
    }),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Query failed (${response.status})`);
  }

  return response.json();
}

export async function askQueryStream(
  query,
  documentScope,
  chatHistory,
  callbacks,
) {
  const { onToken, onRetry, onDone, onError } = callbacks;

  const response = await fetch(`${API_BASE_URL}/query/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      document_scope: documentScope,
      chat_history: chatHistory,
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
      else if (eventType === "done") onDone(parsed);
    }
  }
}
