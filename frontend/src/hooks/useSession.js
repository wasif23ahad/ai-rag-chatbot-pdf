/**
 * useSession.js — Session ID persistence via localStorage.
 *
 * Generates a UUID v4 session ID on first visit and persists it across
 * page refreshes. Allows users to continue a conversation after reload.
 */

import { useState } from 'react';

const SESSION_KEY = 'rag_chatbot_session_id';

/** Minimal UUID v4 generator (no library dependency). */
function generateUUID() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback for older browsers
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/** Load from localStorage or create a new ID. */
function getOrCreateSession() {
  try {
    const stored = localStorage.getItem(SESSION_KEY);
    if (stored) return stored;
    const fresh = generateUUID();
    localStorage.setItem(SESSION_KEY, fresh);
    return fresh;
  } catch {
    // Private browsing: fall back to in-memory ID
    return generateUUID();
  }
}

/**
 * Hook: returns the current session ID and a reset function.
 * Call resetSession() after a new document upload to start fresh.
 */
export function useSession() {
  const [sessionId, setSessionId] = useState(getOrCreateSession);

  const resetSession = () => {
    const fresh = generateUUID();
    try { localStorage.setItem(SESSION_KEY, fresh); } catch { /* ignore */ }
    setSessionId(fresh);
  };

  return { sessionId, resetSession };
}
