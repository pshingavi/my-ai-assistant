'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import { AnimatePresence } from 'framer-motion';
import dynamic from 'next/dynamic';

import { useLMSStore } from '@/src/store/lmsStore';
import {
  fetchTopics,
  fetchTopic,
  fetchTopicNeighbors,
  generateBytes,
  generateBuild,
} from '@/src/lib/api';
import type { TopicSummary, ByteContent, BuildContent, TopicNeighbors, LearningMode } from '@/src/types';

import ByteCard from '@/src/components/ByteCard';
import BuildCard from '@/src/components/BuildCard';
import ConceptDots from '@/src/components/ConceptDots';
import SkeletonCard from '@/src/components/SkeletonCard';

// Dynamic imports for D3-heavy / side-effects components
const TopicSidebar = dynamic(() => import('@/src/components/TopicSidebar'), { ssr: false });
const MiniMap = dynamic(() => import('@/src/components/MiniMap'), { ssr: false });
const ShareModal = dynamic(() => import('@/src/components/ShareModal'), { ssr: false });

const MODES: { id: LearningMode; label: string }[] = [
  { id: 'learn', label: '🧠 Learn' },
  { id: 'build', label: '🏗️ Build' },
  { id: 'share', label: '🚀 Share' },
];

export default function LearnPage() {
  const params = useParams<{ topicId: string }>();
  const topicId = params?.topicId ?? '';

  const {
    currentConceptIndex,
    currentMode,
    byteCache,
    buildCache,
    setTopic,
    setConceptIndex,
    setMode,
    cacheBytes,
    cacheBuild,
    markVisited,
  } = useLMSStore();

  const [allTopics, setAllTopics] = useState<TopicSummary[]>([]);
  const [topic, setTopicData] = useState<TopicSummary | null>(null);
  const [neighbors, setNeighbors] = useState<TopicNeighbors>({ prerequisites: [], next: [], related: [] });
  const [loadingContent, setLoadingContent] = useState(false);
  const [byteContent, setByteContent] = useState<ByteContent | null>(null);
  const [buildContent, setBuildContent] = useState<BuildContent | null>(null);
  const [loadError, setLoadError] = useState('');

  // Load sidebar topics
  useEffect(() => {
    fetchTopics().then(setAllTopics).catch(console.error);
  }, []);

  // Load topic + neighbors when topicId changes
  useEffect(() => {
    if (!topicId) return;
    setTopic(topicId);
    markVisited(topicId);
    setByteContent(null);
    setBuildContent(null);
    setLoadError('');

    Promise.all([
      fetchTopic(topicId),
      fetchTopicNeighbors(topicId),
    ]).then(([t, n]) => {
      setTopicData(t);
      setNeighbors(n);
    }).catch(() => {
      setLoadError('Could not load topic — is the API server running on port 8001?');
    });
  }, [topicId, setTopic, markVisited]);

  const concept = topic?.concepts[currentConceptIndex] ?? '';
  const byteKey = `${topicId}:${concept}`;

  const loadByte = useCallback(async () => {
    if (!topic || !concept) return;
    if (byteCache[byteKey]) {
      setByteContent(byteCache[byteKey]);
      return;
    }
    setLoadingContent(true);
    setLoadError('');
    try {
      const content = await generateBytes(topicId, concept);
      cacheBytes(byteKey, content);
      setByteContent(content);
    } catch {
      setLoadError('Failed to generate byte — check API server.');
    } finally {
      setLoadingContent(false);
    }
  }, [topic, concept, topicId, byteKey, byteCache, cacheBytes]);

  const loadBuild = useCallback(async () => {
    if (!topic || !concept) return;
    if (buildCache[byteKey]) {
      setBuildContent(buildCache[byteKey]);
      return;
    }
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

  // Auto-load content when mode or concept changes
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

  const handleModeChange = (mode: LearningMode) => {
    setMode(mode);
    setByteContent(null);
    setBuildContent(null);
  };

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: '#0a0a0f' }}>

      {/* Left sidebar — full height, scrollable internally */}
      <div className="w-52 shrink-0 hidden md:flex flex-col" style={{ height: '100vh' }}>
        <TopicSidebar topics={allTopics} currentTopicId={topicId} />
      </div>

      {/* Main content — vertically scrollable */}
      <main className="flex-1 min-w-0 overflow-y-auto" style={{ height: '100vh' }}>
        <div className="p-6 lg:p-8 max-w-2xl">
          {topic ? (
            <>
              {/* Topic header */}
              <div className="mb-6">
                <div className="flex items-center gap-2 flex-wrap mb-2">
                  {topic.is_post ? (
                    <span className="badge-post">Generated Post</span>
                  ) : (
                    topic.module_number && (
                      <span className="badge-module">Module {topic.module_number}</span>
                    )
                  )}
                  {topic.source_url && (
                    <a
                      href={topic.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs transition-colors"
                      style={{ color: '#475569' }}
                    >
                      &#128206; View source &rarr;
                    </a>
                  )}
                </div>
                <h1 className="text-2xl font-bold" style={{ color: '#f1f5f9' }}>
                  {topic.name}
                </h1>
                <p className="text-sm mt-1 leading-relaxed" style={{ color: '#64748b' }}>
                  {topic.description}
                </p>
              </div>

              {/* Mode tabs */}
              <div
                className="flex gap-1 mb-6 p-1 rounded-xl w-fit"
                style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)' }}
              >
                {MODES.map((m) => (
                  <button
                    key={m.id}
                    onClick={() => handleModeChange(m.id)}
                    className="px-4 py-1.5 rounded-lg text-sm font-medium transition-all duration-200"
                    style={
                      currentMode === m.id
                        ? {
                            background: 'rgba(139,92,246,0.25)',
                            color: '#e2e8f0',
                            border: '1px solid rgba(139,92,246,0.4)',
                          }
                        : { color: '#64748b', border: '1px solid transparent' }
                    }
                  >
                    {m.label}
                  </button>
                ))}
              </div>

              {/* Concept dots */}
              {currentMode !== 'share' && topic.concepts.length > 0 && (
                <div className="mb-6">
                  <ConceptDots
                    concepts={topic.concepts}
                    currentIndex={currentConceptIndex}
                    onSelect={handleConceptChange}
                  />
                </div>
              )}

              {/* Content area */}
              <div>
                {currentMode === 'share' ? (
                  <ShareModal topic={topic} />
                ) : loadingContent ? (
                  <SkeletonCard />
                ) : loadError ? (
                  <div
                    className="rounded-xl p-4 text-sm"
                    style={{
                      background: 'rgba(248,113,113,0.08)',
                      border: '1px solid rgba(248,113,113,0.25)',
                      color: '#fca5a5',
                    }}
                  >
                    {loadError}
                  </div>
                ) : (
                  <AnimatePresence mode="wait">
                    {currentMode === 'learn' && byteContent && (
                      <ByteCard key={byteKey} content={byteContent} />
                    )}
                    {currentMode === 'build' && buildContent && (
                      <BuildCard key={`build-${byteKey}`} content={buildContent} />
                    )}
                    {((currentMode === 'learn' && !byteContent) ||
                      (currentMode === 'build' && !buildContent)) &&
                      !loadingContent && (
                        <div
                          className="text-sm text-center py-16 rounded-xl"
                          style={{
                            color: '#475569',
                            background: 'rgba(255,255,255,0.02)',
                            border: '1px solid rgba(255,255,255,0.05)',
                          }}
                        >
                          {concept ? `Preparing &ldquo;${concept}&rdquo;...` : 'Select a concept above to begin'}
                        </div>
                      )}
                  </AnimatePresence>
                )}
              </div>

              {/* Concept navigation */}
              {currentMode !== 'share' && topic.concepts.length > 1 && (
                <div
                  className="flex justify-between items-center mt-8 pt-4"
                  style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}
                >
                  <button
                    onClick={() => handleConceptChange(Math.max(0, currentConceptIndex - 1))}
                    disabled={currentConceptIndex === 0}
                    className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed"
                    style={{
                      background: 'rgba(255,255,255,0.05)',
                      color: '#94a3b8',
                      border: '1px solid rgba(255,255,255,0.08)',
                    }}
                  >
                    &larr; Previous Concept
                  </button>
                  <span className="text-xs" style={{ color: '#475569' }}>
                    {currentConceptIndex + 1} / {topic.concepts.length}
                  </span>
                  <button
                    onClick={() =>
                      handleConceptChange(
                        Math.min(topic.concepts.length - 1, currentConceptIndex + 1)
                      )
                    }
                    disabled={currentConceptIndex === topic.concepts.length - 1}
                    className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed"
                    style={{
                      background: 'rgba(139,92,246,0.18)',
                      color: '#c4b5fd',
                      border: '1px solid rgba(139,92,246,0.3)',
                    }}
                  >
                    Next Concept &rarr;
                  </button>
                </div>
              )}
            </>
          ) : (
            <div
              className="flex items-center justify-center"
              style={{ minHeight: '70vh' }}
            >
              {loadError ? (
                <div className="text-center space-y-3 max-w-sm">
                  <p className="text-sm" style={{ color: '#fca5a5' }}>{loadError}</p>
                  <code
                    className="block text-xs px-3 py-2 rounded-lg"
                    style={{ background: 'rgba(255,255,255,0.05)', color: '#94a3b8' }}
                  >
                    uv run python api_server.py
                  </code>
                </div>
              ) : (
                <div className="text-center space-y-3">
                  <div
                    className="w-10 h-10 rounded-full border-2 border-t-transparent animate-spin mx-auto"
                    style={{ borderColor: '#8b5cf6', borderTopColor: 'transparent' }}
                  />
                  <p className="text-sm" style={{ color: '#475569' }}>Loading topic...</p>
                </div>
              )}
            </div>
          )}
        </div>
      </main>

      {/* Right mini-map — fixed panel */}
      {topic && (
        <div
          className="hidden lg:flex flex-col p-4 pt-6"
          style={{
            height: '100vh',
            width: 184,
            flexShrink: 0,
            borderLeft: '1px solid rgba(139,92,246,0.1)',
          }}
        >
          <MiniMap currentTopic={topic} neighbors={neighbors} />
        </div>
      )}
    </div>
  );
}
