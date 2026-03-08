'use client';

import { motion } from 'framer-motion';
import type { ByteContent } from '@/src/types';

interface ByteCardProps {
  content: ByteContent;
}

function SourceChip({ source }: { source: string }) {
  const fileName = source.split('/').pop() || source;
  const displayName = fileName.length > 28 ? fileName.slice(0, 25) + '...' : fileName;
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
      style={{ background: 'rgba(139,92,246,0.1)', color: '#a78bfa', border: '1px solid rgba(139,92,246,0.2)' }}
      title={source}
    >
      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
        <polyline points="14,2 14,8 20,8" />
      </svg>
      {displayName}
    </span>
  );
}

export default function ByteCard({ content }: ByteCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -16 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
      className="space-y-4"
    >
      {/* Header: Emoji + concept name */}
      <div className="flex items-start gap-4">
        <div
          className="flex-shrink-0 w-16 h-16 rounded-2xl flex items-center justify-center text-3xl"
          style={{ background: 'rgba(139,92,246,0.15)', border: '1px solid rgba(139,92,246,0.3)' }}
        >
          {content.emoji || '🧠'}
        </div>
        <div>
          <h2 className="text-xl font-bold" style={{ color: '#f1f5f9' }}>
            {content.concept}
          </h2>
          <p className="text-sm mt-0.5" style={{ color: '#64748b' }}>
            from <span style={{ color: '#8b5cf6' }}>{content.topic_name}</span>
          </p>
        </div>
      </div>

      {/* Analogy section — purple card */}
      <div
        className="rounded-xl p-4"
        style={{ background: 'rgba(139,92,246,0.08)', border: '1px solid rgba(139,92,246,0.2)' }}
      >
        <div className="flex items-center gap-2 mb-2">
          <span className="text-base">💡</span>
          <span className="text-xs font-bold uppercase tracking-wider" style={{ color: '#8b5cf6' }}>
            Think of it like...
          </span>
        </div>
        <p className="text-sm leading-relaxed" style={{ color: '#d4d4d8' }}>
          {content.analogy}
        </p>
      </div>

      {/* Technical explanation */}
      <div
        className="rounded-xl p-4"
        style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)' }}
      >
        <div className="flex items-center gap-2 mb-2">
          <span className="text-base">📖</span>
          <span className="text-xs font-bold uppercase tracking-wider" style={{ color: '#94a3b8' }}>
            Technical Explanation
          </span>
        </div>
        <p className="text-sm leading-relaxed" style={{ color: '#cbd5e1' }}>
          {content.explanation}
        </p>
      </div>

      {/* Why it matters — cyan accent */}
      <div
        className="rounded-xl p-4"
        style={{ background: 'rgba(34,211,238,0.05)', borderLeft: '3px solid #22d3ee', paddingLeft: 16 }}
      >
        <div className="flex items-center gap-2 mb-2">
          <span className="text-base">🚀</span>
          <span className="text-xs font-bold uppercase tracking-wider" style={{ color: '#22d3ee' }}>
            Why It Matters
          </span>
        </div>
        <p className="text-sm leading-relaxed" style={{ color: '#cbd5e1' }}>
          {content.why_it_matters}
        </p>
      </div>

      {/* Sources */}
      {content.sources && content.sources.length > 0 && (
        <div className="flex items-start gap-2 flex-wrap pt-1">
          <span className="text-xs mt-0.5" style={{ color: '#475569' }}>Sources:</span>
          {content.sources.map((src, i) => (
            <SourceChip key={i} source={src} />
          ))}
        </div>
      )}
    </motion.div>
  );
}
