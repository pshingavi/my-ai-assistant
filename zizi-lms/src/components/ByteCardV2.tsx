'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import dynamic from 'next/dynamic';
import type { CachedByte, ByteContent } from '@/src/types';

const PlayerWrapper = dynamic(() => import('./remotion/PlayerWrapper'), { ssr: false });

// Section component with expand/collapse
function Section({ title, icon, children, defaultOpen = true }: {
  title: string; icon: string; children: React.ReactNode; defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between py-4 px-6 text-left"
        style={{ background: 'transparent' }}
      >
        <span className="flex items-center gap-2 text-sm font-semibold" style={{ color: '#94a3b8' }}>
          <span>{icon}</span> {title}
        </span>
        <motion.span
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          style={{ color: '#475569', fontSize: 12 }}
        >▼</motion.span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: 'easeInOut' }}
            style={{ overflow: 'hidden' }}
          >
            <div className="px-6 pb-6">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// Source pill
function SourcePill({ source }: { source: string }) {
  const name = source.split('/').pop() || source;
  const short = name.length > 40 ? name.slice(0, 37) + '…' : name;
  const isPDF = source.endsWith('.pdf');
  const isNB = source.endsWith('.ipynb');
  const color = isPDF ? '#8b5cf6' : isNB ? '#22d3ee' : '#64748b';
  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs"
      style={{ background: `${color}15`, border: `1px solid ${color}44`, color }}>
      {isPDF ? '📄' : isNB ? '📓' : '📝'} {short}
    </span>
  );
}

interface ByteCardV2Props {
  content: CachedByte | ByteContent;
  onRegenerate?: () => void;
  isRegenerating?: boolean;
  version?: number;
}

export default function ByteCardV2({ content, onRegenerate, isRegenerating, version }: ByteCardV2Props) {
  const [showSources, setShowSources] = useState(false);
  const hasImage = 'image_url' in content && content.image_url;
  const hasAnimation = 'animation_props' in content && content.animation_props && content.animation_props.type !== 'none';

  return (
    <motion.div
      key={content.concept}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
      className="relative overflow-hidden"
      style={{
        background: 'rgba(10, 10, 20, 0.85)',
        border: '1px solid rgba(139,92,246,0.2)',
        borderRadius: 24,
        backdropFilter: 'blur(20px)',
        boxShadow: '0 0 60px rgba(139,92,246,0.08)',
      }}
    >
      {/* Ambient top glow */}
      <div style={{
        position: 'absolute', top: 0, left: '20%', right: '20%', height: 1,
        background: 'linear-gradient(90deg, transparent, rgba(139,92,246,0.6), transparent)',
      }} />

      {/* Hero analogy section */}
      <div className="px-8 pt-10 pb-8" style={{ background: 'linear-gradient(180deg, rgba(139,92,246,0.06) 0%, transparent 100%)' }}>
        {/* Emoji */}
        <motion.div
          initial={{ scale: 0, rotate: -20 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ type: 'spring', damping: 8, stiffness: 100, delay: 0.1 }}
          className="text-6xl mb-6 block"
          style={{ lineHeight: 1 }}
        >
          {content.emoji}
        </motion.div>

        {/* Concept label */}
        <div className="text-xs font-bold uppercase tracking-widest mb-3"
          style={{ color: '#8b5cf6', letterSpacing: '0.2em' }}>
          {content.concept}
        </div>

        {/* Analogy — big gradient headline */}
        <motion.h2
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, duration: 0.5 }}
          className="text-2xl sm:text-3xl font-bold leading-snug"
          style={{
            background: 'linear-gradient(135deg, #f1f5f9 0%, #c4b5fd 50%, #67e8f9 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
          }}
        >
          {content.analogy}
        </motion.h2>

        {/* Regenerate controls */}
        {onRegenerate && (
          <div className="flex items-center gap-3 mt-5">
            <button
              onClick={onRegenerate}
              disabled={isRegenerating}
              className="flex items-center gap-2 px-4 py-2 rounded-full text-xs font-medium transition-all duration-200"
              style={{
                background: isRegenerating ? 'rgba(139,92,246,0.1)' : 'rgba(139,92,246,0.15)',
                border: '1px solid rgba(139,92,246,0.3)',
                color: isRegenerating ? '#64748b' : '#c4b5fd',
                cursor: isRegenerating ? 'not-allowed' : 'pointer',
              }}
            >
              <motion.span
                animate={isRegenerating ? { rotate: 360 } : { rotate: 0 }}
                transition={isRegenerating ? { duration: 1, repeat: Infinity, ease: 'linear' } : {}}
              >↺</motion.span>
              {isRegenerating ? 'Generating new analogy…' : 'Try a different analogy'}
            </button>
            {version && version > 1 && (
              <span className="text-xs" style={{ color: '#334155' }}>v{version}</span>
            )}
          </div>
        )}
      </div>

      {/* Media zone — Remotion animation OR DALL-E image */}
      {(hasAnimation || hasImage) && (
        <div className="mx-6 mb-2 overflow-hidden" style={{ borderRadius: 16 }}>
          {hasAnimation && 'animation_props' in content && content.animation_props ? (
            <div style={{ background: '#07070d', borderRadius: 16, overflow: 'hidden' }}>
              <PlayerWrapper animationProps={content.animation_props} />
            </div>
          ) : hasImage && 'image_url' in content && content.image_url ? (
            <div style={{ position: 'relative', aspectRatio: '16/9' }}>
              <img
                src={content.image_url}
                alt={`Visual for ${content.concept}`}
                style={{
                  width: '100%', height: '100%', objectFit: 'cover',
                  borderRadius: 16,
                }}
              />
              <div style={{
                position: 'absolute', inset: 0, borderRadius: 16,
                background: 'linear-gradient(to top, rgba(7,7,13,0.7) 0%, transparent 60%)',
              }} />
            </div>
          ) : null}
        </div>
      )}

      {/* Technical breakdown section */}
      <Section title="Technical Breakdown" icon="⚙️">
        <p className="text-sm leading-relaxed" style={{ color: '#94a3b8', whiteSpace: 'pre-wrap' }}>
          {content.explanation}
        </p>
      </Section>

      {/* Why it matters */}
      <Section title="Why It Matters" icon="💡">
        <div className="rounded-xl p-4" style={{
          background: 'rgba(34,211,238,0.06)',
          border: '1px solid rgba(34,211,238,0.15)',
        }}>
          <p className="text-sm leading-relaxed" style={{ color: '#67e8f9' }}>
            {content.why_it_matters}
          </p>
        </div>
      </Section>

      {/* Sources */}
      {content.sources && content.sources.length > 0 && (
        <div className="px-6 py-4">
          <button
            onClick={() => setShowSources(v => !v)}
            className="flex items-center gap-1.5 text-xs transition-colors mb-3"
            style={{ color: showSources ? '#8b5cf6' : '#475569' }}
          >
            <motion.span animate={{ rotate: showSources ? 90 : 0 }} transition={{ duration: 0.2 }}>▶</motion.span>
            📚 {content.sources.length} source{content.sources.length !== 1 ? 's' : ''}
          </button>
          <AnimatePresence>
            {showSources && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                style={{ overflow: 'hidden' }}
              >
                <div className="flex flex-wrap gap-2">
                  {content.sources.map((s, i) => <SourcePill key={i} source={s} />)}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
    </motion.div>
  );
}
