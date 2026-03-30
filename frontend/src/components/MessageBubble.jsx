/**
 * MessageBubble.jsx — Renders a single message in the conversation thread.
 *
 * Handles:
 *   - User messages (right-aligned, purple accent)
 *   - AI messages  (left-aligned, neutral)
 *   - Error bubbles (red accent)
 *   - Typing indicator (AI loading state)
 *   - Source citations (AI only)
 *   - Grounded / not-grounded tag
 */

import React from 'react';
import SourceCitation from './SourceCitation';

/** Format ISO timestamp to readable "HH:MM" */
function formatTime(iso) {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

/**
 * Typing indicator — three bouncing dots.
 */
export function TypingIndicator() {
  return (
    <div className="message-row ai" aria-label="Assistant is typing">
      <div className="message-avatar" aria-hidden="true">🤖</div>
      <div className="message-body">
        <div className="message-bubble ai-bubble" aria-live="polite">
          <div className="typing-indicator" role="status">
            <div className="typing-dot" />
            <div className="typing-dot" />
            <div className="typing-dot" />
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * @param {Object}  props
 * @param {import('../hooks/useChat').Message} props.message
 */
export default function MessageBubble({ message }) {
  const isUser = message.role === 'user';
  const isError = Boolean(message.error);

  return (
    <article
      className={`message-row ${isUser ? 'user' : 'ai'}`}
      aria-label={`${isUser ? 'You' : 'Assistant'}: ${message.content.slice(0, 60)}`}
    >
      {/* Avatar */}
      <div className="message-avatar" aria-hidden="true">
        {isUser ? '👤' : '🤖'}
      </div>

      {/* Body */}
      <div className="message-body">
        {/* Bubble */}
        <div
          className={`message-bubble ${isError ? 'error' : ''}`}
          role={isError ? 'alert' : undefined}
        >
          {message.content}
        </div>

        {/* AI metadata row: grounded tag + time */}
        {!isUser && !isError && (
          <div className="flex gap-2" style={{ alignItems: 'center', flexWrap: 'wrap' }}>
            {typeof message.isGrounded === 'boolean' && (
              <span
                className={`grounded-tag ${message.isGrounded ? 'yes' : 'no'}`}
                title={message.isGrounded ? 'Grounded in document' : 'Not grounded'}
              >
                {message.isGrounded ? '✓ Grounded' : '⚠ Not grounded'}
              </span>
            )}
            {message.processingTimeMs != null && (
              <span className="text-muted" style={{ fontSize: '10px' }}>
                {message.processingTimeMs}ms
              </span>
            )}
          </div>
        )}

        {/* Source citations (AI only, when not error) */}
        {!isUser && !isError && message.sources?.length > 0 && (
          <SourceCitation sources={message.sources} />
        )}

        {/* Timestamp */}
        <time
          className="message-time"
          dateTime={message.timestamp}
          aria-label={`Sent at ${formatTime(message.timestamp)}`}
        >
          {formatTime(message.timestamp)}
        </time>
      </div>
    </article>
  );
}
