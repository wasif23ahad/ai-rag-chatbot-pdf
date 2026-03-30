/**
 * api.js — Axios API client for the RAG Document Chatbot.
 *
 * All requests are proxied through Vite's dev server (/api → http://localhost:8000)
 * so no CORS issues in development. In production, Nginx handles the proxy.
 */

import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '';

export const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

// ── Request interceptor ────────────────────────────────────────
api.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error),
);

// ── Response interceptor — normalise errors ───────────────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.response?.data?.error ||
      error.message ||
      'An unexpected error occurred.';
    return Promise.reject(new Error(message));
  },
);

// ── API helpers ────────────────────────────────────────────────

/**
 * Upload a document (PDF or DOCX) for ingestion.
 * @param {File} file
 * @returns {Promise<{ status, doc_name, chunk_count, message }>}
 */
export const ingestDocument = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/api/ingest', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

/**
 * Send a chat message.
 * @param {string} sessionId  UUID4 session identifier
 * @param {string} question   User question text
 * @returns {Promise<ChatResponse>}
 */
export const sendMessage = (sessionId, question) =>
  api.post('/api/chat', { session_id: sessionId, question });

/**
 * Fetch backend health status.
 * @returns {Promise<HealthResponse>}
 */
export const getHealth = () => api.get('/api/health');
