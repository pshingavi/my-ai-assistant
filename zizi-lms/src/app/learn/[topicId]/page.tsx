'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import dynamic from 'next/dynamic';

import { useLMSStore } from '@/src/store/lmsStore';
import {
  fetchTopics, fetchTopic, fetchTopicNeighbors,
  generateBytes,
  fetchCachedByte,
  fetchClaudeInteraction,
} from '@/src/lib/api';
import type { TopicSummary, ByteContent, TopicNeighbors, LearningMode, CachedByte } from '@/src/types';

import ByteCardV2 from '@/src/components/ByteCardV2';
import SkeletonCard from '@/src/components/SkeletonCard';
import ConceptDots from '@/src/components/ConceptDots';
import ThemeToggle from '@/src/components/ThemeToggle';

const TopicDrawer = dynamic(() => import('@/src/components/TopicDrawer'), { ssr: false });
const BuildCard   = dynamic(() => import('@/src/components/BuildCard'),   { ssr: false });
const ShareModal  = dynamic(() => import('@/src/components/ShareModal'),  { ssr: false });

const MODES: { id: LearningMode; label: string; icon: string; desc: string }[] = [
  { id: 'learn', label: 'Learn',  icon: '🧠', desc: 'Analogy-first micro-lesson' },
  { id: 'build', label: 'Build',  icon: '🏗️', desc: 'Hands-on interactive code'  },
  { id: 'share', label: 'Share',  icon: '🚀', desc: 'Generate a LinkedIn post'   },
];

export default function LearnPage() {
  const params  = useParams<{ topicId: string }>();
  const router  = useRouter();
  const topicId = params?.topicId ?? '';

  const {
    currentConceptIndex, currentMode, byteCache,
    setTopic, setConceptIndex, setMode, cacheBytes, markVisited,
  } = useLMSStore();

  const [allTopics, setAllTopics]     = useState<TopicSummary[]>([]);
  const [topic, setTopicData]         = useState<TopicSummary | null>(null);
  const [neighbors, setNeighbors]     = useState<TopicNeighbors>({ prerequisites: [], next: [], related: [] });
  const [loadingContent, setLoadingContent] = useState(false);
  const [byteContent, setByteContent]  = useState<CachedByte | ByteContent | null>(null);
  const [loadError, setLoadError]      = useState('');
  const [drawerOpen, setDrawerOpen]    = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [buildHasCode, setBuildHasCode] = useState<boolean | null>(null);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === '[' || e.key === 'm') setDrawerOpen(v => !v);
      if (e.key === 'Escape') setDrawerOpen(false);
      if (e.key === 'ArrowRight' && !e.metaKey) {
        setConceptIndex(Math.min((topic?.concepts.length ?? 1) - 1, currentConceptIndex + 1));
      }
      if (e.key === 'ArrowLeft' && !e.metaKey) {
        setConceptIndex(Math.max(0, currentConceptIndex - 1));
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [topic, currentConceptIndex, setConceptIndex]);

  useEffect(() => { fetchTopics().then(setAllTopics).catch(console.error); }, []);

  useEffect(() => {
    if (!topicId) return;
    setTopicData(null);       // clear stale topic immediately when navigating
    setTopic(topicId);
    markVisited(topicId);
    setByteContent(null);
    setLoadError('');
    Promise.all([fetchTopic(topicId), fetchTopicNeighbors(topicId)])
      .then(([t, n]) => { setTopicData(t); setNeighbors(n); })
      .catch(() => setLoadError('Could not load topic — is the API server running?'));
  }, [topicId, setTopic, markVisited]);

  const concept = topic?.concepts[currentConceptIndex] ?? '';
  const byteKey = `${topicId}:${concept}`;

  const loadByte = useCallback(async (forceRegenerate = false) => {
    if (!topic || !concept) return;
    // Read byteCache directly from store to avoid stale-closure re-renders
    const cache = useLMSStore.getState().byteCache;
    if (!forceRegenerate && cache[byteKey]) {
      setByteContent(cache[byteKey]);
      return;
    }
    setLoadingContent(true);
    setLoadError('');
    try {
      if (forceRegenerate) {
        setIsRegenerating(true);
        // Use fetchCachedByte after regeneration triggers via RegeneratePanel
        const cached = await fetchCachedByte(topicId, concept);
        if (cached) {
          cacheBytes(byteKey, cached as unknown as ByteContent);
          setByteContent(cached);
        }
      } else {
        const cached = await fetchCachedByte(topicId, concept);
        if (cached) {
          cacheBytes(byteKey, cached as unknown as ByteContent);
          setByteContent(cached);
        } else {
          const content = await generateBytes(topicId, concept);
          cacheBytes(byteKey, content);
          setByteContent(content);
        }
      }
    } catch {
      setLoadError('Failed to load byte — check API server.');
    } finally {
      setLoadingContent(false);
      setIsRegenerating(false);
    }
  // byteCache intentionally excluded — read fresh from store.getState() to keep callback stable
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topic, concept, topicId, byteKey, cacheBytes]);

  useEffect(() => {
    if (!topic || !concept) return;
    setByteContent(null);
    setLoadError('');
    if (currentMode === 'learn' || currentMode === 'share') {
      loadByte();
    } else {
      // build mode: BuildCard fetches its own content — clear any stale loading state
      setLoadingContent(false);
    }
  }, [currentMode, concept, topic, loadByte]);

  // Background check: does this concept have hands-on code snippets?
  useEffect(() => {
    if (!byteContent || !topicId || !concept) return;
    setBuildHasCode(null); // reset to unknown while checking
    fetchClaudeInteraction(topicId, concept)
      .then(result => {
        const steps: { code_snippet?: string }[] = result.steps ?? [];
        const hasCode = steps.some(s => (s.code_snippet || '').trim().length > 5);
        setBuildHasCode(hasCode);
      })
      .catch(() => setBuildHasCode(true)); // on error keep Build enabled
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [byteContent, topicId, concept]);

  const handleConceptChange = (idx: number) => {
    if (idx === currentConceptIndex) return;
    setConceptIndex(idx);
    setByteContent(null);
    setBuildHasCode(null);
  };

  const handleByteRefresh = useCallback((byte: CachedByte) => {
    cacheBytes(byteKey, byte as unknown as ByteContent);
    setByteContent(byte);
  }, [byteKey, cacheBytes]);

  const handleNext = () => {
    if (!topic) return;
    if (currentConceptIndex < topic.concepts.length - 1) {
      handleConceptChange(currentConceptIndex + 1);
    } else if (neighbors.next[0]) {
      router.push(`/learn/${neighbors.next[0].id}`);
    }
  };

  const handlePrev = () => {
    if (currentConceptIndex > 0) {
      handleConceptChange(currentConceptIndex - 1);
    } else if (neighbors.prerequisites[0]) {
      router.push(`/learn/${neighbors.prerequisites[0].id}`);
    }
  };

  const isLastConcept  = topic ? currentConceptIndex === topic.concepts.length - 1 : false;
  const canGoNext      = !isLastConcept || !!neighbors.next[0];
  const canGoPrev      = currentConceptIndex > 0 || !!neighbors.prerequisites[0];
  const totalConcepts  = topic?.concepts.length ?? 0;
  const progress       = totalConcepts > 1 ? ((currentConceptIndex) / (totalConcepts - 1)) * 100 : 100;

  return (
    <div className="min-h-screen" style={{ background: 'var(--bg)' }}>
      {/* Ambient blobs */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden" style={{ zIndex: 0 }}>
        <div className="absolute -top-60 -right-60 w-[800px] h-[800px] rounded-full"
          style={{ background: 'radial-gradient(circle, rgba(124,58,237,0.05) 0%, transparent 70%)', filter: 'blur(100px)' }} />
        <div className="absolute -bottom-60 -left-60 w-[700px] h-[700px] rounded-full"
          style={{ background: 'radial-gradient(circle, rgba(6,182,212,0.03) 0%, transparent 70%)', filter: 'blur(100px)' }} />
      </div>

      <TopicDrawer
        topics={allTopics}
        currentTopicId={topicId}
        currentConcept={concept}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onConceptSelect={(tid, cidx) => {
          if (tid === topicId) {
            handleConceptChange(cidx);
          } else {
            router.push(`/learn/${tid}`);
          }
        }}
      />

      {/* ── Header ── */}
      <header className="sticky top-0 z-30 flex items-center justify-between px-5 py-4"
        style={{
          background: 'var(--surface-2)',
          backdropFilter: 'blur(24px)',
          borderBottom: '1px solid var(--border)',
        }}
      >
        {/* Left: menu + logo + topic */}
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <motion.button
            onClick={() => setDrawerOpen(v => !v)}
            whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
            className="flex flex-col gap-1.5 p-2.5 rounded-xl flex-shrink-0"
            style={{ border: '1px solid var(--border)', background: drawerOpen ? 'var(--accent-soft)' : 'transparent' }}
            title="Topics menu [M]"
          >
            {[0,1,2].map(i => (
              <motion.span
                key={i}
                animate={drawerOpen ? (i === 1 ? { opacity: 0 } : { rotate: i === 0 ? 45 : -45, y: i === 0 ? 6 : -6 }) : { rotate: 0, y: 0, opacity: 1 }}
                transition={{ duration: 0.2 }}
                className="block w-4 h-0.5 rounded"
                style={{ background: drawerOpen ? '#7c3aed' : 'var(--text-4)' }}
              />
            ))}
          </motion.button>

          <Link href="/" className="flex-shrink-0 font-bold text-lg select-none" style={{ color: 'var(--accent)' }}>⚡</Link>

          {topic && (
            <div className="flex items-center gap-2 min-w-0">
              {topic.module_number && !topic.is_post && (
                <span className="text-xs px-2 py-0.5 rounded-full font-mono font-bold flex-shrink-0"
                  style={{ background: 'rgba(124,58,237,0.1)', color: '#7c3aed', border: '1px solid rgba(124,58,237,0.2)' }}>
                  {topic.module_number}
                </span>
              )}
              <h1 className="font-semibold text-sm truncate" style={{ color: 'var(--text-1)' }}>{topic.name}</h1>
              {totalConcepts > 1 && (
                <span className="text-xs flex-shrink-0 hidden sm:block" style={{ color: 'var(--text-4)' }}>
                  · {currentConceptIndex + 1}/{totalConcepts}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Right: nav links + theme */}
        <div className="flex items-center gap-1 flex-shrink-0">
          {[{ href: '/', label: 'Home' }, { href: '/chat', label: 'Chat' }].map(n => (
            <Link key={n.href} href={n.href}
              className="px-3 py-1.5 rounded-lg text-xs font-medium hidden md:block transition-colors"
              style={{ color: 'var(--text-4)' }}
              onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = 'var(--text-2)'; }}
              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = 'var(--text-4)'; }}
            >
              {n.label}
            </Link>
          ))}
          <ThemeToggle />
        </div>
      </header>

      {/* Progress bar */}
      {topic && totalConcepts > 1 && (
        <div className="relative z-20 h-0.5" style={{ background: 'var(--border)' }}>
          <motion.div
            className="absolute left-0 top-0 h-full"
            style={{ background: 'linear-gradient(90deg, #7c3aed, #a855f7)', borderRadius: '0 2px 2px 0' }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.4, ease: 'easeOut' }}
          />
        </div>
      )}

      {/* ── Main ── */}
      <main className="relative z-10 flex" style={{ minHeight: 'calc(100vh - 57px)' }}>

        {/* LEFT ARROW */}
        <div className="fixed left-0 top-1/2 -translate-y-1/2 z-20 pl-2 sm:pl-4">
          <motion.button
            onClick={handlePrev}
            disabled={!canGoPrev}
            whileHover={canGoPrev ? { scale: 1.12, x: -2 } : {}}
            whileTap={canGoPrev ? { scale: 0.92 } : {}}
            className="w-11 h-11 rounded-full flex items-center justify-center text-2xl disabled:opacity-0"
            style={{
              background: canGoPrev ? 'var(--surface)' : 'transparent',
              border: `1px solid ${canGoPrev ? 'var(--border)' : 'transparent'}`,
              color: '#7c3aed',
              boxShadow: canGoPrev ? '0 4px 20px rgba(124,58,237,0.18)' : 'none',
              backdropFilter: 'blur(12px)',
            }}
          >‹</motion.button>
        </div>

        {/* RIGHT ARROW */}
        <div className="fixed right-0 top-1/2 -translate-y-1/2 z-20 pr-2 sm:pr-4">
          <motion.button
            onClick={handleNext}
            disabled={!canGoNext}
            whileHover={canGoNext ? { scale: 1.12, x: 2 } : {}}
            whileTap={canGoNext ? { scale: 0.92 } : {}}
            className="w-11 h-11 rounded-full flex items-center justify-center text-2xl disabled:opacity-0"
            style={{
              background: canGoNext ? 'var(--surface)' : 'transparent',
              border: `1px solid ${canGoNext ? 'var(--border)' : 'transparent'}`,
              color: '#7c3aed',
              boxShadow: canGoNext ? '0 4px 20px rgba(124,58,237,0.18)' : 'none',
              backdropFilter: 'blur(12px)',
            }}
          >›</motion.button>
        </div>

        {/* Card column */}
        <div className="flex-1 flex flex-col py-10 px-14 sm:px-18" style={{ maxWidth: 1040, margin: '0 auto', width: '100%' }}>

          {/* Concept dots + counter */}
          {topic && totalConcepts > 1 && (
            <motion.div
              initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }}
              className="mb-8 flex flex-col items-center gap-2"
            >
              <ConceptDots
                concepts={topic.concepts}
                currentIndex={currentConceptIndex}
                onSelect={handleConceptChange}
              />
            </motion.div>
          )}

          {/* Concept pill */}
          {concept && (
            <motion.div
              key={concept}
              initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
              className="mb-7 self-center"
            >
              <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider"
                style={{
                  background: 'rgba(124,58,237,0.08)',
                  border: '1px solid rgba(124,58,237,0.2)',
                  color: '#7c3aed',
                  letterSpacing: '0.1em',
                }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#7c3aed', display: 'inline-block' }} />
                {concept}
              </span>
            </motion.div>
          )}

          {/* Mode selector — inline, prominent */}
          <div className="mb-6 flex rounded-2xl overflow-hidden self-stretch"
            style={{ border: '1px solid rgba(124,58,237,0.15)', background: 'var(--surface)' }}>
            {MODES.map((m, i) => {
              const isBuildDisabled = m.id === 'build' && buildHasCode === false;
              return (
                <motion.button
                  key={m.id}
                  onClick={() => !isBuildDisabled && setMode(m.id)}
                  className="flex-1 flex flex-col items-center gap-1 py-4 px-3 relative"
                  whileHover={isBuildDisabled ? {} : { scale: 1.01 }}
                  whileTap={isBuildDisabled ? {} : { scale: 0.98 }}
                  title={isBuildDisabled ? 'No hands-on code for this concept — try Interactive or Chat' : undefined}
                  style={{
                    cursor: isBuildDisabled ? 'not-allowed' : 'pointer',
                    opacity: isBuildDisabled ? 0.45 : 1,
                    ...(currentMode === m.id ? {
                      background: 'linear-gradient(135deg, rgba(124,58,237,0.12), rgba(124,58,237,0.06))',
                    } : {}),
                  }}
                >
                  {/* Divider between tabs */}
                  {i > 0 && <div className="absolute left-0 top-1/4 bottom-1/4 w-px" style={{ background: 'rgba(124,58,237,0.12)' }} />}

                  <span style={{ fontSize: 20 }}>{m.icon}</span>
                  <span className="text-xs font-bold" style={{ color: currentMode === m.id ? '#7c3aed' : 'var(--text-3)' }}>
                    {m.label}
                  </span>
                  <span className="text-xs hidden sm:block" style={{ color: 'var(--text-5)', fontSize: 10 }}>
                    {isBuildDisabled ? 'No code for this concept' : m.desc}
                  </span>
                  {currentMode === m.id && !isBuildDisabled && (
                    <motion.div
                      layoutId="mode-indicator"
                      className="absolute bottom-0 left-4 right-4 h-0.5 rounded-full"
                      style={{ background: '#7c3aed' }}
                    />
                  )}
                </motion.button>
              );
            })}
          </div>

          {/* Content area — no intermediate placeholder state to avoid AnimatePresence key flicker */}
          <AnimatePresence mode="wait">
            {currentMode === 'share' && topic ? (
              <motion.div key="share"
                initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.3 }}
              >
                <ShareModal
                  topic={topic}
                  currentConcept={concept}
                  byteAnalogy={byteContent && 'analogy' in byteContent ? (byteContent as CachedByte).analogy : undefined}
                  byteImageUrl={byteContent && 'image_url' in byteContent ? (byteContent as any).image_url : undefined}
                />
              </motion.div>
            ) : currentMode === 'build' ? (
              <motion.div key={byteKey + '-build'}
                initial={{ opacity: 0, y: 16, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -12 }}
                transition={{ duration: 0.35, ease: [0.4, 0, 0.2, 1] }}
              >
                <BuildCard
                  topicId={topicId}
                  concept={concept}
                  topicName={topic?.name ?? ''}
                />
              </motion.div>
            ) : byteContent ? (
              <motion.div key={byteKey + '-learn'}
                initial={{ opacity: 0, y: 16, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -12, scale: 0.98 }}
                transition={{ duration: 0.35, ease: [0.4, 0, 0.2, 1] }}
              >
                <ByteCardV2
                  content={byteContent}
                  topicId={topicId}
                  concept={concept}
                  onRegenerate={() => loadByte(true)}
                  onByteRefresh={handleByteRefresh}
                  isRegenerating={isRegenerating}
                  version={'version' in byteContent ? byteContent.version : undefined}
                />
              </motion.div>
            ) : loadError ? (
              <motion.div key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                className="rounded-3xl p-8 text-sm text-center"
                style={{ background: 'rgba(220,38,38,0.04)', border: '1px solid rgba(220,38,38,0.12)', color: '#dc2626' }}>
                {loadError}
                <button
                  onClick={() => loadByte()}
                  className="mt-4 block mx-auto px-4 py-2 rounded-xl text-xs font-semibold"
                  style={{ background: 'rgba(220,38,38,0.08)', border: '1px solid rgba(220,38,38,0.15)', color: '#dc2626' }}
                >
                  Retry
                </button>
              </motion.div>
            ) : (
              <motion.div key={byteKey + '-skeleton'} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}>
                <SkeletonCard />
              </motion.div>
            )}
          </AnimatePresence>

          {/* Up next */}
          {topic && isLastConcept && neighbors.next[0] && currentMode !== 'share' && (
            <motion.div
              initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }}
              className="mt-12 flex flex-col items-center gap-5"
            >
              <div className="flex items-center gap-3 w-full max-w-sm">
                <div className="flex-1 h-px" style={{ background: 'var(--border)' }} />
                <span className="text-xs font-bold uppercase tracking-widest" style={{ color: 'var(--text-4)', letterSpacing: '0.1em' }}>
                  Module Complete
                </span>
                <div className="flex-1 h-px" style={{ background: 'var(--border)' }} />
              </div>
              <div className="text-center">
                <div className="text-2xl mb-2">🎉</div>
                <p className="text-sm font-medium mb-4" style={{ color: 'var(--text-3)' }}>
                  Ready for the next module?
                </p>
                <Link href={`/learn/${neighbors.next[0].id}`}
                  className="inline-flex items-center gap-3 px-7 py-3.5 rounded-2xl text-sm font-bold transition-all hover:scale-105"
                  style={{
                    background: 'linear-gradient(135deg, #7c3aed, #6d28d9)',
                    color: '#fff',
                    boxShadow: '0 4px 24px rgba(124,58,237,0.4)',
                  }}
                >
                  <span>{neighbors.next[0].name}</span>
                  <span>→</span>
                </Link>
              </div>
            </motion.div>
          )}

          {/* Bottom keyboard hint */}
          <p className="text-center text-xs mt-8 hidden sm:block" style={{ color: 'var(--text-5)', opacity: 0.5 }}>
            ← → to navigate · [M] for menu · [Esc] to close
          </p>
        </div>
      </main>

      {/* No topic fallback */}
      {!topic && !loadError && (
        <div className="fixed inset-0 flex items-center justify-center z-0">
          <div className="text-center space-y-4">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1.2, repeat: Infinity, ease: 'linear' }}
              className="w-10 h-10 rounded-full border-2 mx-auto"
              style={{ borderColor: 'rgba(124,58,237,0.15)', borderTopColor: '#7c3aed' }}
            />
            <p className="text-xs font-medium" style={{ color: '#a78bfa' }}>Loading topic…</p>
          </div>
        </div>
      )}

      {loadError && !topic && (
        <div className="fixed inset-0 flex items-center justify-center z-0">
          <div className="text-center space-y-4 p-8">
            <p className="text-sm" style={{ color: '#dc2626' }}>⚠️ {loadError}</p>
            <code className="block text-xs px-4 py-2 rounded-xl"
              style={{ background: 'var(--accent-soft)', color: 'var(--text-5)', border: '1px solid var(--border)' }}>
              uv run python api_server.py
            </code>
          </div>
        </div>
      )}
    </div>
  );
}
