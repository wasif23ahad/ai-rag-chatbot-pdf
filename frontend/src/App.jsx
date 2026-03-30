/**
 * App.jsx — Root application layout.
 *
 * Layout:
 *   Header
 *   └─ app-content (flex row)
 *       ├─ Sidebar
 *       │   ├─ UploadPanel
 *       │   └─ Session info card
 *       └─ ChatWindow
 */

import React from 'react';
import UploadPanel from './components/UploadPanel';
import ChatWindow from './components/ChatWindow';
import { useChat } from './hooks/useChat';

export default function App() {
  const { messages, isLoading, sessionId, submitQuestion, clearMessages } = useChat();

  // When a doc is successfully ingested, reset chat context
  const handleUploadSuccess = (docName, chunkCount) => {
    clearMessages();
  };

  const hasDocument = messages.some((m) => m.role === 'user') || false;

  return (
    <div className="app-shell">
      {/* ── Header ──────────────────────────────────────────── */}
      <header className="app-header" role="banner">
        <div className="app-logo">
          <div className="app-logo-icon" aria-hidden="true">⚡</div>
          <span className="app-logo-text">RAG Document Chatbot</span>
        </div>

        <div className="app-status-badge" aria-label="System status">
          <span className="status-dot" aria-hidden="true" />
          Powered by Grok&nbsp;3
        </div>
      </header>

      {/* ── Main Content ─────────────────────────────────────── */}
      <main className="app-content" role="main" aria-label="Application content">
        {/* ── Sidebar ─────────────────────────────────────── */}
        <aside className="sidebar" aria-label="Document sidebar">
          {/* Document upload */}
          <UploadPanel onUploadSuccess={handleUploadSuccess} />

          {/* Session info */}
          <div className="card" aria-label="Session information">
            <p className="card-title">🔑 Session</p>
            <div className="session-info">
              <div className="session-row">
                <span className="session-label">ID</span>
                <span
                  className="session-value"
                  title={sessionId}
                  aria-label={`Session ID: ${sessionId}`}
                >
                  {sessionId}
                </span>
              </div>
              <div className="session-row">
                <span className="session-label">Messages</span>
                <span className="session-value">{messages.length}</span>
              </div>
            </div>
          </div>

          {/* How-it-works card */}
          <div className="card" aria-label="How it works guide">
            <p className="card-title">💡 How it works</p>
            <ol
              style={{
                paddingLeft: '18px',
                fontSize: '12px',
                color: 'var(--text-secondary)',
                lineHeight: 1.8,
                display: 'flex',
                flexDirection: 'column',
                gap: '4px',
              }}
            >
              <li>Upload a <strong>PDF</strong> or <strong>DOCX</strong> document</li>
              <li>Ask any question about the content</li>
              <li>Grok 3 answers <em>only</em> from the document</li>
              <li>Click <strong>{'>'}  sources</strong> to see match details</li>
            </ol>
          </div>
        </aside>

        {/* ── Chat Window ──────────────────────────────────── */}
        <ChatWindow
          messages={messages}
          isLoading={isLoading}
          onSubmit={submitQuestion}
          disabled={false}
        />
      </main>
    </div>
  );
}
