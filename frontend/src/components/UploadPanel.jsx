/**
 * UploadPanel.jsx — Document upload panel with drag-and-drop support.
 *
 * States:
 *   idle     → Dropzone (click or drag)
 *   loading  → Progress animation
 *   success  → File name + chunk count displayed
 *   error    → Error message shown, dropzone re-enabled
 *
 * On success: calls onUploadSuccess(docName, chunkCount) so the parent
 * can reset the chat session.
 */

import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { ingestDocument } from '../services/api';

const ACCEPTED_TYPES = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
};

const MAX_SIZE_BYTES = 50 * 1024 * 1024; // 50 MB

/**
 * @param {Object}   props
 * @param {Function} props.onUploadSuccess  (docName, chunkCount) => void
 */
export default function UploadPanel({ onUploadSuccess }) {
  const [status, setStatus] = useState('idle'); // 'idle'|'loading'|'success'|'error'
  const [docInfo, setDocInfo] = useState(null);   // { name, chunkCount }
  const [errorMsg, setErrorMsg] = useState('');

  const processFile = useCallback(async (file) => {
    setStatus('loading');
    setErrorMsg('');

    try {
      const { data } = await ingestDocument(file);
      setDocInfo({ name: data.doc_name, chunkCount: data.chunk_count });
      setStatus('success');
      onUploadSuccess?.(data.doc_name, data.chunk_count);
    } catch (err) {
      setErrorMsg(err.message || 'Upload failed. Please try again.');
      setStatus('error');
    }
  }, [onUploadSuccess]);

  const onDrop = useCallback(
    (accepted, rejected) => {
      if (rejected.length > 0) {
        const reason = rejected[0]?.errors?.[0]?.message ?? 'Invalid file.';
        setErrorMsg(reason);
        setStatus('error');
        return;
      }
      if (accepted.length > 0) processFile(accepted[0]);
    },
    [processFile],
  );

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxSize: MAX_SIZE_BYTES,
    maxFiles: 1,
    disabled: status === 'loading',
    noClick: false,
    noKeyboard: false,
  });

  const handleReplaceDoc = () => {
    setStatus('idle');
    setDocInfo(null);
    setErrorMsg('');
  };

  return (
    <div className="card" aria-label="Document upload">
      <p className="card-title">📄 Document</p>

      {/* ── Success state ── */}
      {status === 'success' && docInfo ? (
        <>
          <div className="upload-success" role="status" aria-live="polite">
            <span className="upload-success-icon" aria-hidden="true">✅</span>
            <div>
              <div className="upload-success-name" title={docInfo.name}>
                {docInfo.name}
              </div>
              <div className="upload-success-meta">
                {docInfo.chunkCount} chunks indexed · Ready for chat
              </div>
            </div>
          </div>
          <button
            id="replace-doc-btn"
            onClick={handleReplaceDoc}
            style={{
              marginTop: '12px',
              width: '100%',
              padding: '8px',
              background: 'none',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--text-muted)',
              fontSize: '12px',
              cursor: 'pointer',
              transition: 'color 150ms, border-color 150ms',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = 'var(--text-primary)';
              e.currentTarget.style.borderColor = 'rgba(255,255,255,0.2)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = 'var(--text-muted)';
              e.currentTarget.style.borderColor = 'var(--border-subtle)';
            }}
          >
            ↩ Replace document
          </button>
        </>
      ) : (
        /* ── Idle / loading / error state ── */
        <>
          <div
            {...getRootProps()}
            id="upload-dropzone"
            className={`upload-zone ${isDragActive ? 'drag-active' : ''} ${status === 'loading' ? 'uploading' : ''}`}
            aria-label="Upload a PDF or DOCX document by clicking or dragging"
            role="button"
            tabIndex={0}
          >
            <input {...getInputProps()} aria-hidden="true" />
            <span className="upload-icon" aria-hidden="true">
              {status === 'loading' ? '⏳' : '📂'}
            </span>
            <p className="upload-title">
              {isDragActive
                ? 'Drop your file here…'
                : status === 'loading'
                ? 'Processing document…'
                : 'Drop a PDF or DOCX here'}
            </p>
            <p className="upload-subtitle">
              or <em>click to browse</em> · Max 50 MB
            </p>
          </div>

          {status === 'loading' && (
            <div className="upload-progress" role="progressbar" aria-label="Uploading">
              <div className="upload-progress-bar">
                <div className="upload-progress-fill" />
              </div>
            </div>
          )}

          {(status === 'error' || errorMsg) && (
            <div className="upload-error" role="alert" aria-live="assertive">
              <span aria-hidden="true">⚠</span>
              {errorMsg}
            </div>
          )}
        </>
      )}
    </div>
  );
}
