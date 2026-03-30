/**
 * useChat.js — Message state management and chat API integration.
 *
 * Responsibilities:
 *   - Maintain the list of conversation messages
 *   - Fire POST /api/chat and append the response
 *   - Track loading state for the typing indicator
 *   - Handle API errors gracefully (append error bubble)
 */

import { useState, useCallback } from 'react';
import { sendMessage } from '../services/api';
import { useSession } from './useSession';

/**
 * @typedef {Object} Message
 * @property {string}   id          Unique message key
 * @property {'user'|'ai'} role     Message sender
 * @property {string}   content     Text content
 * @property {boolean}  [error]     Is this an error bubble?
 * @property {Array}    [sources]   Source citations from backend
 * @property {boolean}  [isGrounded]
 * @property {number}   [processingTimeMs]
 * @property {string}   timestamp   ISO string
 */

let _msgCounter = 0;
function nextId() { return `msg_${Date.now()}_${++_msgCounter}`; }

export function useChat() {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const { sessionId, resetSession } = useSession();

  /** Append a message to the list (immutable). */
  const appendMessage = useCallback((msg) => {
    setMessages((prev) => [...prev, msg]);
  }, []);

  /** Send a user question through the RAG pipeline. */
  const submitQuestion = useCallback(
    async (question) => {
      if (!question.trim() || isLoading) return;

      // 1. Optimistically add the user bubble
      appendMessage({
        id: nextId(),
        role: 'user',
        content: question.trim(),
        timestamp: new Date().toISOString(),
      });

      // 2. Show loading state
      setIsLoading(true);

      try {
        // 3. Call the backend
        const { data } = await sendMessage(sessionId, question.trim());

        // 4. Append the AI response
        appendMessage({
          id: nextId(),
          role: 'ai',
          content: data.answer,
          sources: data.sources ?? [],
          isGrounded: data.is_grounded,
          processingTimeMs: data.processing_time_ms,
          timestamp: new Date().toISOString(),
        });
      } catch (err) {
        // 5. Append error bubble (never expose full error to user)
        const message =
          err.message?.includes('Invalid input detected')
            ? 'Your message was flagged as potentially unsafe and could not be processed.'
            : err.message || 'Something went wrong. Please try again.';

        appendMessage({
          id: nextId(),
          role: 'ai',
          content: message,
          error: true,
          timestamp: new Date().toISOString(),
        });
      } finally {
        setIsLoading(false);
      }
    },
    [sessionId, isLoading, appendMessage],
  );

  /** Clear all messages (called on new document upload). */
  const clearMessages = useCallback(() => {
    setMessages([]);
    resetSession();
  }, [resetSession]);

  return {
    messages,
    isLoading,
    sessionId,
    submitQuestion,
    clearMessages,
  };
}
