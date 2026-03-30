/**
 * SourceCitation.jsx — Expandable source citations for AI responses.
 *
 * Shows: "{N} sources found" collapsed by default.
 * Expands to: chunk preview (200 chars), page number, similarity badge.
 * Covers T9 requirements.
 */

import React, { useState } from 'react';
import SimilarityBadge from './SimilarityBadge';

/**
 * @param {Object}   props
 * @param {Array}    props.sources  Array of SourceChunk from backend
 */
export default function SourceCitation({ sources }) {
  const [open, setOpen] = useState(false);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="source-citation" aria-label="Source citations">
      <button
        id="sources-toggle-btn"
        className="sources-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls="sources-list-panel"
      >
        <span className={`sources-toggle-arrow ${open ? 'open' : ''}`}>▶</span>
        {sources.length} source{sources.length !== 1 ? 's' : ''} found
      </button>

      {open && (
        <ul
          id="sources-list-panel"
          className="sources-list"
          role="list"
        >
          {sources.map((src, idx) => (
            <li key={src.chunk_id ?? idx} className="source-item" role="listitem">
              <div className="source-header">
                <span className="source-label">Chunk {idx + 1}</span>
                <span className="source-page" aria-label={`Page ${src.page}`}>
                  p.{src.page}
                </span>
                <SimilarityBadge score={src.similarity_score} />
              </div>
              <p className="source-preview">
                {(src.text_preview || '').slice(0, 200)}
                {src.text_preview?.length > 200 ? '…' : ''}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
