/**
 * API client for the Infrragment backend.
 * All endpoints are proxied through Vite dev server at /api.
 */

const BASE = '';

/**
 * Upload a PDF file for processing.
 * @param {File} file
 * @returns {Promise<{upload_id: string, filename: string, total_pages: number}>}
 */
export async function uploadPDF(file) {
  const form = new FormData();
  form.append('file', file);

  const res = await fetch(`${BASE}/api/upload`, {
    method: 'POST',
    body: form,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Upload failed');
  }

  return res.json();
}

/**
 * Connect to the SSE status stream for an upload.
 * @param {string} uploadId
 * @param {(status: object) => void} onUpdate
 * @returns {{ close: () => void }}
 */
export function streamStatus(uploadId, onUpdate) {
  const es = new EventSource(`${BASE}/api/status/${uploadId}`);

  es.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onUpdate(data);
    } catch {
      // skip malformed messages
    }
  };

  es.onerror = () => {
    // EventSource will auto-reconnect, but we also provide a fallback
    console.warn('SSE connection error, will retry...');
  };

  return {
    close: () => es.close(),
  };
}

/**
 * Get all documents for a processed upload.
 * @param {string} uploadId
 */
export async function getDocuments(uploadId) {
  const res = await fetch(`${BASE}/api/documents/${uploadId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to load documents');
  }
  return res.json();
}

/**
 * Get the URL for a document instance's PDF.
 * @param {string} uploadId
 * @param {string} docInstanceId
 * @returns {string}
 */
export function getDocumentPdfUrl(uploadId, docInstanceId) {
  return `${BASE}/api/documents/${uploadId}/${docInstanceId}/pdf`;
}

/**
 * Get extracted tables for a document instance.
 * @param {string} uploadId
 * @param {string} docInstanceId
 */
export async function getDocumentTables(uploadId, docInstanceId) {
  const res = await fetch(`${BASE}/api/tables/${uploadId}/${docInstanceId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to load tables');
  }
  return res.json();
}

/**
 * Get efficiency statistics for a processed upload.
 * @param {string} uploadId
 */
export async function getEfficiencyStats(uploadId) {
  const res = await fetch(`${BASE}/api/efficiency/${uploadId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to load efficiency stats');
  }
  return res.json();
}

/**
 * Poll processing status (fallback for SSE).
 * @param {string} uploadId
 */
export async function pollStatus(uploadId) {
  const res = await fetch(`${BASE}/api/status-poll/${uploadId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to poll status');
  }
  return res.json();
}

/**
 * List all previously processed uploads.
 */
export async function listUploads() {
  const res = await fetch(`${BASE}/api/uploads`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to list uploads');
  }
  return res.json();
}
