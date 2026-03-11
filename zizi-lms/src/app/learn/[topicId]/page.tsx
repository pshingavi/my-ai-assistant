'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import dynamic from 'next/dynamic';

import { useLMSStore } from '@/src/store/lmsStore';
import {
  fetchTopics, fetchTopic, fetchTopicNeighbors,
  generateBytes, generateBuild,
  fetchCachedByte, regenerateByte,
} from '@/src/lib/api';
import type { TopicSummary, ByteContent, BuildContent, TopicNeighbors, LearningMode, CachedByte } from '@/src/types';

import ByteCardV2 from '@/src/components/ByteCardV2';
import SkeletonCard from '@/src/components/SkeletonCard';
import ConceptDots from '@/src/components/ConceptDots';

const TopicDrawer = dynamic(() => import('@/src/components/TopicDrawer'), { ssr: false });
const BuildCard = dynamic(() => import('@/src/components/BuildCard'), { ssr: false });
const ShareModal = dynamic(() => import('@/src/components/ShareModal'), { ssr: false });

const MODES: { id: LearningMode; label: string; icon: string }[] = [
  { id: 'learn', label: 'Learn', icon: '🧠' },
  { id: 'build', label: 'Build', icon: '🏗️' },
  { id: 'share', label: 'Share', icon: '🚀' },
];

export default function LearnPage() {
  const params = useParams<{ topicId: string }>();
  const router = useRouter();
  const topicId = params?.topicId ?? '';

  const {
    currentConceptIndex, currentMode, byteCache, buildCache,
    setTopic, setConceptIndex, setMode, cacheBytes, cacheBuild, markVisited,
  } = useLMSStore();

  const [allTopics, setAllTopics] = useState<TopicSummary[]>([]);
  const [topic, setTopicData] = useState<TopicSummary | null>(null);
  const [neighbors, setNeighbors] = useState<TopicNeighbors>({ prerequisites: [], next: [], related: [] });
  const [loadingContent, setLoadingContent] = useState(false);
  const [byteContent, setByteContent] = useState<CachedByte | ByteContent | null>(null);
  const [buildContent, setBuildContent] = useState<BuildContent | null>(null);
  const [loadError, setLoadError] = useState('');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);

  // Load sidebar topics
  useEffect(() => {
    fetchTopics().then(setAllTopics).catch(console.error);
  }, []);

  // Keyboard shortcut for drawer
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === '[') setDrawerOpen(v => !v);
      if (e.key === 'Escape') setDrawerOpen(false);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  // Load topic + neighbors
  useEffect(() => {
    if (!topicId) return;
    setTopic(topicId);
    markVisited(topicId);
    setByteContent(null);
    setBuildContent(null);
    setLoadError('');
    Promise.all([fetchTopic(topicId), fetchTopicNeighbors(topicId)])
      .then(([t, n]) => { setTopicData(t); setNeighbors(n); })
      .catch(() => setLoadError('Could not load topic — is the API server running on port 8001?'));
  }, [topicId, setTopic, markVisited]);

  const concept = topic?.concepts[currentConceptIndex] ?? '';
  const byteKey = `${topicId}:${concept}`;

  const loadByte = useCallback(async (forceRegenerate = false) => {
    if (!topic || !concept) return;

    // Check Zustand cache first (for non-regenerate loads)
    if (!forceRegenerate && byteCache[byteKey]) {
      setByteContent(byteCache[byteKey]);
      return;
    }

    setLoadingContent(true);
    setLoadError('');
    try {
      if (forceRegenerate) {
        setIsRegenerating(true);
        const fresh = await regenerateByte(topicId, concept);
        cacheBytes(byteKey, fresh as unknown as ByteContent);
        setByteContent(fresh);
      } else {
        // Try SQLite cache first for rich content (image + animation)
        const cached = await fetchCachedByte(topicId, concept);
        if (cached) {
          cacheBytes(byteKey, cached as unknown as ByteContent);
          setByteContent(cached);
        } else {
          // Fallback: generate on demand
          const content = await generateBytes(topicId, concept);
          cacheBytes(byteKey, content);
          setByteContent(content);
        }
      }
    } catch {
      setLoadError('Failed to generate byte — check API server.');
    } finally {
      setLoadingContent(false);
      setIsRegenerating(false);
    }
  }, [topic, concept, topicId, byteKey, byteCache, cacheBytes]);

  const loadBuild = useCallback(async () => {
    if (!topic || !concept) return;
    if (buildCache[byteKey]) { setBuildContent(buildCache[byteKey]); return; }
    setLoadingContent(true);
    setLoadError('');
    try {
      const content = await generateBuild(topicId, concept);
      cacheBuild(byteKey, content);
      setBuildContent(content);
    } catch {
      setLoadError('Failed to generate build card — check API server.');
    } finally {
      setLoadingContent(false);
    }
  }, [topic, concept, topicId, byteKey, buildCache, cacheBuild]);

  useEffect(() => {
    if (!topic) return;
    if (currentMode === 'learn') loadByte();
    else if (currentMode === 'build') loadBuild();
  }, [currentMode, concept, topic, loadByte, loadBuild]);

  const handleConceptChange = (idx: number) => {
    setConceptIndex(idx);
    setByteContent(null);
    setBuildContent(null);
  };

  const handleRegenerate = () => loadByte(true);

  const handleNext = () => {
    if (!topic) return;
    const nextNeighbor = neighbors.next[0];
    if (currentConceptIndex < topic.concepts.length - 1) {
      handleConceptChange(currentConceptIndex + 1);
    } else if (nextNeighbor) {
      router.push(`/learn/${nextNeighbor.id}`);
    }
  };

  const isLastConcept = topic ? currentConceptIndex === topic.concepts.length - 1 : false;
  const isFirstConcept = currentConceptIndex === 0;

  return (
    <div className="min-h-screen" style={{ background: '#07070d', color: '#f1f5f9' }}>
      {/* Ambient background */}
      <div className="fixed inset-0 pointer-events-none" style={{ zIndex: 0 }}>
        <div className="absolute top-0 right-1/3 w-[600px] h-[600px] rounded-full"
          style={{ background: 'radial-gradient(circle, rgba(139,92,246,0.06) 0%, transparent 70%)', filter: 'blur(80px)' }} />
        <div className="absolute bottom-1/4 left-1/4 w-[400px] h-[400px] rounded-full"
          style={{ background: 'radial-gradient(circle, rgba(34,211,238,0.04) 0%, transparent 70%)', filter: 'blur(60px)' }} />
      </div>

      {/* Topic drawer */}
      <TopicDrawer
        topics={allTopics}
        currentTopicId={topicId}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      />

      {/* Sticky top bar */}
      <header className="sticky top-0 z-30 flex items-center justify-between px-5 py-3"
        style={{
          borderBottom: '1px solid rgba(139,92,246,0.1)',
          backdropFilter: 'blur(16px)',
          background: 'rgba(7,7,13,0.88)',
        }}>
        <div className="flex items-center gap-3">
          {/* Hamburger / drawer toggle */}
          <button onClick={() => setDrawerOpen(v => !v)}
            className="flex flex-col gap-1 p-2 rounded-lg transition-colors"
            style={{ border: '1px solid rgba(255,255,255,0.08)' }}
            title="Topics [ ]">
            {[0, 1, 2].map(i => (
              <span key={i} className="block w-4 h-0.5 rounded"
                style={{ background: drawerOpen ? '#8b5cf6' : '#475569' }} />
            ))}
          </button>

          <Link href="/" className="text-lg">⚡</Link>

          {topic && (
            <div className="flex items-center gap-2 min-w-0">
              {topic.module_number && !topic.is_post && (
                <span className="text-xs px-2 py-0.5 rounded-full font-mono"
                  style={{ background: 'rgba(139,92,246,0.15)', color: '#8b5cf6', border: '1px solid rgba(139,92,246,0.25)' }}>
                  {topic.module_number}
                </span>
              )}
              <h1 className="font-semibold text-sm truncate" style={{ color: '#e2e8f0' }}>
                {topic.name}
              </h1>
            </div>
          )}
        </div>

        {/* Mode tabs */}
        <div className="flex items-center gap-1 px-1 py-1 rounded-xl"
          style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
          {MODES.map(m => (
            <button key={m.id} onClick={() => { setMode(m.id); setByteContent(null); setBuildContent(null); }}
              className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200"
              style={currentMode === m.id
                ? { background: 'rgba(139,92,246,0.25)', color: '#e2e8f0', border: '1px solid rgba(139,92,246,0.35)' }
                : { color: '#64748b', border: '1px solid transparent' }}>
              {m.icon} {m.label}
            </button>
          ))}
        </div>

        {/* Nav links */}
        <div className="flex items-center gap-1">
          {[{ href: '/', label: 'Galaxy' }, { href: '/chat', label: 'Chat' }].map(n => (
            <Link key={n.href} href={n.href}
              className="px-3 py-1.5 rounded-lg text-xs transition-colors hidden sm:block"
              style={{ color: '#475569', border: '1px solid transparent' }}>
              {n.label}
            </Link>
          ))}
        </div>
      </header>

      {/* Main content */}
      <main className="relative z-10 max-w-3xl mx-auto px-4 sm:px-6 py-8">
        {topic ? (
          <>
            {/* Concept progress dots */}
            {currentMode !== 'share' && topic.concepts.length > 1 && (
              <div className="mb-8">
                <ConceptDots
                  concepts={topic.concepts}
                  currentIndex={currentConceptIndex}
                  onSelect={handleConceptChange}
                />
              </div>
            )}

            {/* Content */}
            <AnimatePresence mode="wait">
              {currentMode === 'share' ? (
                <ShareModal key="share" topic={topic} />
              ) : loadingContent ? (
                <motion.div key="skeleton" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <SkeletonCard />
                </motion.div>
              ) : loadError ? (
                <motion.div key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  className="rounded-2xl p-6 text-sm text-center"
                  style={{ background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)', color: '#fca5a5' }}>
                  {loadError}
                </motion.div>
              ) : currentMode === 'learn' && byteContent ? (
                <ByteCardV2
                  key={byteKey}
                  content={byteContent}
                  onRegenerate={handleRegenerate}
                  isRegenerating={isRegenerating}
                  version={'version' in byteContent ? byteContent.version : undefined}
                />
              ) : currentMode === 'build' && buildContent ? (
                <BuildCard key={`build-${byteKey}`} content={buildContent} />
              ) : !loadingContent && (
                <motion.div key="placeholder" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  className="text-sm text-center py-20 rounded-2xl"
                  style={{ color: '#334155', background: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.04)' }}>
                  {concept ? `Loading "${concept}"…` : 'Select a concept to begin'}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Concept navigation */}
            {currentMode !== 'share' && topic.concepts.length > 0 && (
              <div className="flex justify-between items-center mt-8 pt-6"
                style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                <button
                  onClick={() => handleConceptChange(Math.max(0, currentConceptIndex - 1))}
                  disabled={isFirstConcept}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 disabled:opacity-25 disabled:cursor-not-allowed"
                  style={{ background: 'rgba(255,255,255,0.05)', color: '#94a3b8', border: '1px solid rgba(255,255,255,0.08)' }}>
                  ← Prev
                </button>

                <div className="text-center">
                  <span className="text-xs" style={{ color: '#334155' }}>
                    {currentConceptIndex + 1} / {topic.concepts.length}
                  </span>
                  {isLastConcept && neighbors.next[0] && (
                    <div className="text-xs mt-1" style={{ color: '#475569' }}>
                      Next topic: {neighbors.next[0].name}
                    </div>
                  )}
                </div>

                <button
                  onClick={handleNext}
                  disabled={isLastConcept && !neighbors.next[0]}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 disabled:opacity-25 disabled:cursor-not-allowed"
                  style={{ background: 'rgba(139,92,246,0.18)', color: '#c4b5fd', border: '1px solid rgba(139,92,246,0.3)' }}>
                  {isLastConcept && neighbors.next[0] ? `→ ${neighbors.next[0].name}` : 'Next →'}
                </button>
              </div>
            )}
          </>
        ) : (
          <div className="flex items-center justify-center" style={{ minHeight: '70vh' }}>
            {loadError ? (
              <div className="text-center space-y-4">
                <p className="text-sm" style={{ color: '#fca5a5' }}>{loadError}</p>
                <code className="block text-xs px-4 py-2 rounded-xl"
                  style={{ background: 'rgba(255,255,255,0.04)', color: '#94a3b8', border: '1px solid rgba(255,255,255,0.06)' }}>
                  uv run python api_server.py
                </code>
              </div>
            ) : (
              <div className="text-center space-y-4">
                <div className="w-10 h-10 rounded-full border-2 border-t-transparent animate-spin mx-auto"
                  style={{ borderColor: '#8b5cf6', borderTopColor: 'transparent' }} />
                <p className="text-sm" style={{ color: '#334155' }}>Loading topic…</p>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
