/**
 * SimilarityBadge.jsx — Color-coded confidence badge for source citations.
 *
 * Score thresholds (matching backend similarity_score = 1 / (1 + L2)):
 *   >= 0.75 → High confidence  (green)
 *   >= 0.55 → Medium confidence (yellow/amber)
 *   <  0.55 → Low confidence   (orange)
 */

import React from 'react';

/**
 * @param {Object} props
 * @param {number} props.score  Similarity score [0, 1]
 */
export default function SimilarityBadge({ score }) {
  const pct = Math.round(score * 100);

  const level = score >= 0.75 ? 'high' : score >= 0.55 ? 'medium' : 'low';
  const label = level === 'high' ? '●' : level === 'medium' ? '◐' : '○';

  return (
    <span
      className={`similarity-badge ${level}`}
      title={`Similarity: ${pct}%`}
      aria-label={`${pct}% similarity match`}
    >
      {label} {pct}%
    </span>
  );
}
