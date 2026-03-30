/**
 * ChatWindow.jsx — The main conversation interface.
 *
 * Responsibilities:
 *   - Rendering the message thread (MessageBubble)
 *   - Auto-scrolling to the latest message
 *   - Managing the text input and send action (Enter key / button)
 *   - Showing the TypingIndicator while awaiting an AI response
 *   - Showing the empty state when no messages exist
 */

import React, { useEffect, useRef, useState, useCallback } from 'react';
import MessageBubble, { TypingIndicator } from './MessageBubble';

/**
 * @param {Object}   props
 * @param {Array}    props.messages      Conversation messages
 * @param {boolean}  props.isLoading     Whether the AI is responding
 * @param {Function} props.onSubmit      Callback to send a message
 * @param {boolean}  props.disabled      Block input when no doc is ingested
 */
export default function ChatWindow({ messages, isLoading, onSubmit, disabled }) {
  const [input, setInput] = useState('');
  const bottomRef = useRef(null);
  const textareaRef = useRef(null);

  // Auto-scroll to the latest message whenever anything changes
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Auto-resize textarea as user types
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = `${Math.min(ta.scrollHeight, 140)}px`;
  }, [input]);

  const handleSubmit = useCallback(
    (e) => {
      e.preventDefault();
      if (!input.trim() || isLoading || disabled) return;
      onSubmit(input);
      setInput('');
      // Reset textarea height
      if (textareaRef.current) textareaRef.current.style.height = 'auto';
    },
    [input, isLoading, disabled, onSubmit],
  );

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmit(e);
      }
    },
    [handleSubmit],
  );

  const isEmpty = messages.length === 0 && !isLoading;

  return (
    <section
      className="chat-container"
      aria-label="Chat conversation"
    >
      {/* ── Message list ────────────────────────────────────── */}
      <div
        className="chat-messages"
        role="log"
        aria-live="polite"
        aria-atomic="false"
        aria-label="Conversation messages"
        id="chat-message-list"
      >
        {isEmpty ? (
          <div className="chat-empty" aria-label="No messages yet">
            <span className="chat-empty-icon" aria-hidden="true">💬</span>
            <h2 className="chat-empty-title">Ask your document anything</h2>
            <p className="chat-empty-subtitle">
              Upload a PDF or DOCX in the sidebar, then ask questions about its content.
            </p>
          </div>
        ) : (
          messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))
        )}

        {isLoading && <TypingIndicator />}

        {/* Invisible sentinel for auto-scroll */}
        <div ref={bottomRef} aria-hidden="true" />
      </div>

      {/* ── Input area ──────────────────────────────────────── */}
      <div className="chat-input-area">
        <form
          className="chat-input-form"
          onSubmit={handleSubmit}
          aria-label="Send a message"
        >
          <div className="chat-input-wrapper">
            <label htmlFor="chat-input-field" className="sr-only">
              Ask a question about the document
            </label>
            <textarea
              id="chat-input-field"
              ref={textareaRef}
              className="chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                disabled
                  ? 'Upload a document to start chatting…'
                  : 'Ask a question about the document… (Enter to send)'
              }
              disabled={isLoading || disabled}
              rows={1}
              aria-disabled={isLoading || disabled}
              aria-multiline="true"
              autoComplete="off"
            />
          </div>

          <button
            id="chat-send-btn"
            type="submit"
            className="chat-send-btn"
            disabled={!input.trim() || isLoading || disabled}
            aria-label="Send message"
            title="Send (Enter)"
          >
            {isLoading ? '⏳' : '↑'}
          </button>
        </form>

        <p className="chat-input-hint">
          Shift+Enter for new line · Answers are grounded exclusively in the uploaded document
        </p>
      </div>
    </section>
  );
}
