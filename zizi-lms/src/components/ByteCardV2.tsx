'use client';

import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import dynamic from 'next/dynamic';
import type { CachedByte, ByteContent, P5Sketch } from '@/src/types';
import { fetchClaudeInteraction } from '@/src/lib/api';

const InteractivePlayer = dynamic(() => import('./InteractivePlayer'), { ssr: false });
const RegeneratePanel = dynamic(() => import('./RegeneratePanel'), { ssr: false });

type CardTab = 'analogy' | 'interactive' | 'deepdive';

interface TabDef { id: CardTab; icon: string; label: string }
const ALL_TABS: TabDef[] = [
  { id: 'analogy',     icon: '🖼️', label: 'Analogy'     },
  { id: 'interactive', icon: '🎮', label: 'Interactive'  },
  { id: 'deepdive',   icon: '📖', label: 'Deep Dive'    },
];

function SourcePill({ source }: { source: string }) {
  const name  = source.split('/').pop() || source;
  const short = name.length > 40 ? name.slice(0, 37) + '…' : name;
  const isPDF = source.endsWith('.pdf');
  const isNB  = source.endsWith('.ipynb');
  return (
    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium" style={{
      background: isPDF ? 'rgba(124,58,237,0.08)' : isNB ? 'rgba(8,145,178,0.08)' : 'var(--accent-soft)',
      border:     isPDF ? '1px solid rgba(124,58,237,0.2)' : isNB ? '1px solid rgba(8,145,178,0.2)' : '1px solid var(--border)',
      color:      isPDF ? 'var(--text-5)' : isNB ? '#0e7490' : 'var(--text-4)',
    }}>
      {isPDF ? '📄' : isNB ? '📓' : '📝'} {short}
    </span>
  );
}

interface ByteCardV2Props {
  content:         CachedByte | ByteContent;
  topicId:         string;
  concept:         string;
  onRegenerate?:   () => void;
  onByteRefresh?:  (byte: CachedByte) => void;
  isRegenerating?: boolean;
  version?:        number;
}

export default function ByteCardV2({
  content,
  topicId,
  concept,
  onRegenerate,
  onByteRefresh,
  isRegenerating,
  version,
}: ByteCardV2Props) {
  const imageUrl  = ('image_url' in content && content.image_url) ? content.image_url : null;


  const [activeTab, setActiveTab]           = useState<CardTab>('analogy');
  const [showRegenPanel, setShowRegenPanel] = useState(false);
  const [claudeSketch, setClaudeSketch]     = useState<P5Sketch | null>(null);
  const [claudeLoading, setClaudeLoading]   = useState(false);
  const [claudeError, setClaudeError]       = useState('');

  const loadClaudeSketch = useCallback(async () => {
    if (claudeSketch) return;
    setClaudeLoading(true);
    setClaudeError('');
    try {
      const sketch = await fetchClaudeInteraction(topicId, concept);
      setClaudeSketch(sketch);
    } catch {
      setClaudeError('Zizi Byte could not load the interactive widget.');
    } finally {
      setClaudeLoading(false);
    }
  }, [topicId, concept, claudeSketch]);

  const handleTabChange = (tab: CardTab) => {
    setActiveTab(tab);
    if (tab === 'interactive' && !claudeSketch && !claudeLoading) {
      loadClaudeSketch();
    }
  };

  const handleRegenComplete = (byte: CachedByte, _sketch?: P5Sketch) => {
    setShowRegenPanel(false);
    setClaudeSketch(null);   // force interactive widget to reload with new Claude interaction
    setClaudeError('');
    onByteRefresh?.(byte);
  };

  return (
    <motion.div
      key={content.concept}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
      className="w-full rounded-3xl overflow-hidden"
      style={{ boxShadow: '0 24px 80px rgba(0,0,0,0.15), 0 4px 20px rgba(124,58,237,0.1)' }}
    >
      {/* ══════════════════════════════════════════════════════
          HERO — split layout: text left, image right
      ══════════════════════════════════════════════════════ */}
      <div className="relative flex overflow-hidden" style={{ minHeight: 400 }}>

        {/* ── Left: text content ── */}
        <div className="relative flex-1 flex flex-col justify-between z-10"
          style={{ padding: '36px 40px 36px', background: 'linear-gradient(135deg, var(--bg) 0%, var(--surface) 100%)' }}
        >
          {/* Top row: topic badge + regen */}
          <div className="flex items-start justify-between mb-5">
            {'topic_name' in content && content.topic_name && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold"
                style={{
                  background: 'rgba(124,58,237,0.12)',
                  border: '1px solid rgba(124,58,237,0.25)',
                  color: '#a78bfa',
                }}>
                📚 {content.topic_name}
              </span>
            )}
            <motion.button
              onClick={() => setShowRegenPanel(v => !v)}
              disabled={isRegenerating}
              whileHover={isRegenerating ? {} : { scale: 1.05 }}
              whileTap={isRegenerating ? {} : { scale: 0.95 }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold ml-auto"
              style={{
                background: showRegenPanel ? 'rgba(124,58,237,0.2)' : 'rgba(255,255,255,0.08)',
                border: showRegenPanel ? '1px solid rgba(124,58,237,0.4)' : '1px solid rgba(255,255,255,0.12)',
                color: isRegenerating ? 'rgba(255,255,255,0.35)' : 'rgba(255,255,255,0.8)',
                backdropFilter: 'blur(8px)',
                cursor: isRegenerating ? 'not-allowed' : 'pointer',
              }}
            >
              <motion.span
                animate={isRegenerating ? { rotate: 360 } : {}}
                transition={isRegenerating ? { duration: 1, repeat: Infinity, ease: 'linear' } : {}}
              >↺</motion.span>
              {isRegenerating ? 'Generating…' : 'Regenerate'}
              {version && version > 1 && <span style={{ opacity: 0.4 }}>v{version}</span>}
            </motion.button>
          </div>

          {/* Emoji + Concept heading */}
          <div className="flex items-center gap-4 mb-5">
            <motion.span
              initial={{ scale: 0, rotate: -15 }}
              animate={{ scale: 1, rotate: 0 }}
              transition={{ type: 'spring', damping: 12, stiffness: 140, delay: 0.05 }}
              style={{ fontSize: 44, lineHeight: 1, flexShrink: 0 }}
            >
              {content.emoji}
            </motion.span>
            <motion.h2
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.08, duration: 0.4 }}
              style={{ fontSize: 22, fontWeight: 900, lineHeight: 1.2, color: 'var(--text-1)', letterSpacing: '-0.02em' }}
            >
              {content.concept}
            </motion.h2>
          </div>

          {/* Analogy hero — first sentence only (full analogy lives in Analogy tab) */}
          <motion.blockquote
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.12, duration: 0.5 }}
            style={{
              fontSize: 15,
              fontWeight: 500,
              lineHeight: 1.8,
              color: 'var(--text-2)',
              fontStyle: 'italic',
              flex: 1,
              paddingLeft: 14,
              borderLeft: '3px solid rgba(124,58,237,0.35)',
            }}
          >
            {(() => { const a = content.analogy; const i = a.indexOf('.'); return i > 0 && i < a.length - 1 ? a.slice(0, i + 1) : a; })()}
          </motion.blockquote>
        </div>

        {/* ── Right: image panel ── */}
        <div className="hidden sm:block relative flex-shrink-0"
          style={{ width: 260, background: 'var(--bg)' }}
        >
          {imageUrl ? (
            <>
              {/* eslint-disable-next-line */}
              <img
                src={imageUrl}
                alt=""
                style={{
                  position: 'absolute', inset: 0,
                  width: '100%', height: '100%', objectFit: 'cover',
                  opacity: 0.88,
                }}
              />
              <div style={{
                position: 'absolute', inset: 0,
                background: 'linear-gradient(to right, var(--bg) 0%, transparent 35%)',
              }} />
            </>
          ) : (
            <div style={{
              position: 'absolute', inset: 0,
              background: 'linear-gradient(135deg, rgba(124,58,237,0.15) 0%, rgba(6,182,212,0.08) 100%)',
            }}>
              <div style={{
                position: 'absolute', top: '50%', left: '50%',
                transform: 'translate(-50%, -50%)',
                fontSize: 64, opacity: 0.15,
              }}>
                {content.emoji}
              </div>
            </div>
          )}
        </div>

        {/* Ambient orb */}
        <div style={{
          position: 'absolute', bottom: -80, left: -80, zIndex: 0,
          width: 300, height: 300, borderRadius: '50%',
          background: 'radial-gradient(circle, var(--accent-soft) 0%, transparent 70%)',
          filter: 'blur(50px)', pointerEvents: 'none',
        }} />
      </div>

      {/* ══════════════════════════════════════════════════════
          REGENERATE PANEL (slides in below hero)
      ══════════════════════════════════════════════════════ */}
      <AnimatePresence>
        {showRegenPanel && (
          <RegeneratePanel
            topicId={topicId}
            concept={concept}
            currentAnalogy={content.analogy}
            onClose={() => setShowRegenPanel(false)}
            onComplete={handleRegenComplete}
          />
        )}
      </AnimatePresence>

      {/* ══════════════════════════════════════════════════════
          TAB BAR
      ══════════════════════════════════════════════════════ */}
      <div
        className="flex"
        style={{ background: 'var(--surface)', borderBottom: '2px solid var(--border)' }}
      >
        {ALL_TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => handleTabChange(tab.id)}
            className="flex-1 flex items-center justify-center gap-2 py-4 text-xs font-bold relative transition-colors duration-150"
            style={{
              color:      activeTab === tab.id ? 'var(--accent)' : 'var(--text-4)',
              background: activeTab === tab.id ? 'rgba(124,58,237,0.05)' : 'transparent',
              letterSpacing: '0.02em',
            }}
            onMouseEnter={e => {
              if (activeTab !== tab.id) (e.currentTarget as HTMLElement).style.color = 'var(--text-2)';
            }}
            onMouseLeave={e => {
              if (activeTab !== tab.id) (e.currentTarget as HTMLElement).style.color = 'var(--text-4)';
            }}
          >
            <span style={{ fontSize: 16 }}>{tab.icon}</span>
            <span className="hidden sm:inline">{tab.label}</span>
            {activeTab === tab.id && (
              <motion.div
                layoutId="card-tab-line"
                className="absolute bottom-0 left-0 right-0 h-0.5 rounded-full"
                style={{ background: 'var(--accent)' }}
              />
            )}
          </button>
        ))}
      </div>

      {/* ══════════════════════════════════════════════════════
          TAB CONTENT
      ══════════════════════════════════════════════════════ */}
      <div style={{ background: 'var(--surface)', minHeight: 360 }}>
        <AnimatePresence mode="wait">

          {/* Analogy tab — full analogy + why it matters */}
          {activeTab === 'analogy' && (
            <motion.div key="analogy"
              initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              transition={{ duration: 0.18 }}
              className="p-10"
            >
              <div className="flex items-center gap-4 mb-8">
                <div className="w-12 h-12 rounded-2xl flex items-center justify-center text-2xl flex-shrink-0"
                  style={{ background: 'rgba(124,58,237,0.12)', border: '1px solid rgba(124,58,237,0.25)', boxShadow: '0 4px 16px rgba(124,58,237,0.12)' }}>
                  🖼️
                </div>
                <div>
                  <div className="text-sm font-black uppercase tracking-widest" style={{ color: 'var(--text-1)', letterSpacing: '0.12em' }}>
                    The Analogy
                  </div>
                  <div className="text-xs mt-1" style={{ color: 'var(--text-4)' }}>The mechanism mapped to everyday life</div>
                </div>
              </div>
              <blockquote
                className="rounded-2xl p-7 mb-8"
                style={{ background: 'rgba(124,58,237,0.04)', border: '1px solid rgba(124,58,237,0.12)', borderLeft: '4px solid #7c3aed' }}
              >
                <p className="leading-relaxed" style={{ color: 'var(--text-1)', fontSize: 17, lineHeight: 1.85, fontStyle: 'normal' }}>
                  {content.analogy}
                </p>
              </blockquote>

              {content.why_it_matters && (
                <div className="rounded-2xl p-7"
                  style={{ background: 'rgba(16,185,129,0.04)', border: '1px solid rgba(16,185,129,0.15)' }}>
                  <div className="flex items-center gap-3 mb-4">
                    <span className="text-xl">💡</span>
                    <span className="text-xs font-black uppercase tracking-widest" style={{ color: '#10b981', letterSpacing: '0.14em' }}>
                      Why This Matters
                    </span>
                  </div>
                  <p className="leading-relaxed" style={{ color: 'var(--text-2)', lineHeight: 1.85, fontSize: 15 }}>
                    {content.why_it_matters}
                  </p>
                </div>
              )}
            </motion.div>
          )}

          {/* Interactive tab — Claude widget only */}
          {activeTab === 'interactive' && (
            <motion.div key="interactive"
              initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              transition={{ duration: 0.18 }}
            >
              <div className="p-6">
                {claudeError ? (
                  <div
                    className="rounded-2xl p-8 text-sm text-center"
                    style={{ background: 'rgba(220,38,38,0.04)', border: '1px solid rgba(220,38,38,0.12)', color: '#dc2626' }}
                  >
                    {claudeError}
                    <button
                      onClick={loadClaudeSketch}
                      className="mt-4 block mx-auto px-4 py-2 rounded-xl text-xs font-semibold"
                      style={{ background: 'rgba(220,38,38,0.08)', border: '1px solid rgba(220,38,38,0.15)', color: '#dc2626' }}
                    >
                      Retry
                    </button>
                  </div>
                ) : claudeLoading ? (
                  <div className="flex flex-col items-center justify-center gap-4 py-24">
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1.2, repeat: Infinity, ease: 'linear' }}
                      className="w-10 h-10 rounded-full border-2"
                      style={{ borderColor: 'rgba(124,58,237,0.2)', borderTopColor: '#7c3aed' }}
                    />
                    <p className="text-sm font-medium" style={{ color: '#a78bfa' }}>
                      Zizi Byte is crafting your interactive widget…
                    </p>
                    <p className="text-xs" style={{ color: 'rgba(167,139,250,0.5)' }}>
                      This takes ~20 seconds on first load
                    </p>
                  </div>
                ) : claudeSketch ? (
                  <InteractivePlayer
                    sketchCode={claudeSketch.sketch_code}
                    steps={claudeSketch.steps}
                  />
                ) : (
                  <div className="flex flex-col items-center justify-center gap-4 py-24">
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1.2, repeat: Infinity, ease: 'linear' }}
                      className="w-10 h-10 rounded-full border-2"
                      style={{ borderColor: 'rgba(124,58,237,0.2)', borderTopColor: '#7c3aed' }}
                    />
                    <p className="text-sm" style={{ color: '#a78bfa' }}>Loading…</p>
                  </div>
                )}
              </div>
            </motion.div>
          )}

          {/* Deep Dive tab */}
          {activeTab === 'deepdive' && (
            <motion.div key="deepdive"
              initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              transition={{ duration: 0.18 }}
              className="p-10"
            >
              <div className="flex items-center gap-4 mb-8">
                <div className="w-12 h-12 rounded-2xl flex items-center justify-center text-2xl flex-shrink-0"
                  style={{ background: 'rgba(6,182,212,0.08)', border: '1px solid rgba(6,182,212,0.22)', boxShadow: '0 4px 16px rgba(6,182,212,0.08)' }}>
                  📖
                </div>
                <div>
                  <div className="text-sm font-black uppercase tracking-widest" style={{ color: 'var(--text-1)', letterSpacing: '0.12em' }}>
                    Technical Breakdown
                  </div>
                  <div className="text-xs mt-1" style={{ color: 'var(--text-4)' }}>Go deeper — verbatim from course materials</div>
                </div>
              </div>
              <p className="leading-relaxed whitespace-pre-wrap mb-8"
                style={{ color: 'var(--text-2)', fontSize: 15.5, lineHeight: 1.9 }}>
                {content.explanation}
              </p>
              {content.sources && content.sources.length > 0 && (
                <div className="pt-6" style={{ borderTop: '1px solid var(--border)' }}>
                  <div className="text-xs font-bold mb-4 flex items-center gap-2" style={{ color: 'var(--text-4)' }}>
                    <span style={{ width: 20, height: 1.5, background: 'var(--border-strong)', display: 'inline-block', borderRadius: 2 }} />
                    Sources
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {content.sources.map((s, i) => <SourcePill key={i} source={s} />)}
                  </div>
                </div>
              )}
            </motion.div>
          )}

        </AnimatePresence>
      </div>
    </motion.div>
  );
}
