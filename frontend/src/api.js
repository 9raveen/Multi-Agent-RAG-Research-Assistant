// api.js
// Centralized calls to the FastAPI backend. Keeps the base URL in one place
// so switching from local dev to a deployed backend later is a one-line change.

const BASE_URL = "http://127.0.0.1:8000";

export async function uploadPdf(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${BASE_URL}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Upload failed (${response.status})`);
  }

  return response.json();
}

export async function askQuery(query, documentScope = null) {
  const response = await fetch(`${BASE_URL}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, document_scope: documentScope }),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Query failed (${response.status})`);
  }

  return response.json();
}
