import { Suspense } from 'react';
import Link from 'next/link';
import { fetchTopics, fetchKG } from '@/src/lib/api';
import TopicGalaxyWrapper from '@/src/components/TopicGalaxyWrapper';
import type { TopicSummary } from '@/src/types';

export const dynamic = 'force-dynamic';

export default async function HomePage() {
  const [topics, kgData] = await Promise.all([
    fetchTopics().catch(() => [] as TopicSummary[]),
    fetchKG().catch(() => ({ nodes: [], edges: [] })),
  ]);

  const firstTopic = topics[0];
  const courseTopics = topics.filter((t) => !t.is_post);
  const postTopics = topics.filter((t) => t.is_post);

  return (
    <main
      className="min-h-screen flex flex-col"
      style={{ background: '#0a0a0f' }}
    >
      {/* Ambient gradient blobs */}
      <div
        className="fixed inset-0 pointer-events-none"
        aria-hidden="true"
        style={{ zIndex: 0 }}
      >
        <div
          className="absolute top-0 left-1/4 w-96 h-96 rounded-full opacity-10"
          style={{ background: 'radial-gradient(circle, #8b5cf6, transparent 70%)', filter: 'blur(60px)' }}
        />
        <div
          className="absolute bottom-1/4 right-1/4 w-80 h-80 rounded-full opacity-10"
          style={{ background: 'radial-gradient(circle, #22d3ee, transparent 70%)', filter: 'blur(60px)' }}
        />
      </div>

      {/* Nav */}
      <nav
        className="relative z-10 flex items-center justify-between px-6 py-4"
        style={{ borderBottom: '1px solid rgba(139,92,246,0.1)' }}
      >
        <div className="flex items-center gap-2">
          <span className="text-2xl" aria-label="lightning">&#9889;</span>
          <span className="font-extrabold text-lg" style={{ color: '#8b5cf6' }}>
            Zizi Byte
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span
            className="px-3 py-1 rounded-full text-xs font-medium"
            style={{ background: 'rgba(139,92,246,0.1)', color: '#8b5cf6', border: '1px solid rgba(139,92,246,0.2)' }}
          >
            {topics.length} topics
          </span>
          {firstTopic && (
            <Link
              href={`/learn/${firstTopic.id}`}
              className="px-4 py-2 rounded-lg text-sm font-semibold text-white transition"
              style={{ background: '#8b5cf6' }}
            >
              Start Learning
            </Link>
          )}
        </div>
      </nav>

      {/* Hero */}
      <div className="relative z-10 flex flex-col items-center text-center pt-16 pb-10 px-6">
        <div
          className="inline-flex items-center gap-2 text-sm font-medium mb-6 rounded-full px-4 py-1.5"
          style={{ background: 'rgba(139,92,246,0.1)', color: '#a78bfa', border: '1px solid rgba(139,92,246,0.25)' }}
        >
          <span>&#10024;</span>
          Adaptive AI Micro-Learning Platform
        </div>

        <h1
          className="text-5xl sm:text-6xl font-extrabold mb-4 tracking-tight"
          style={{ color: '#f1f5f9' }}
        >
          Zizi{' '}
          <span
            style={{
              background: 'linear-gradient(135deg, #8b5cf6 0%, #22d3ee 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            Byte
          </span>
        </h1>

        <p
          className="text-xl italic mb-3 font-light"
          style={{ color: '#94a3b8' }}
        >
          &ldquo;Learn in bytes. Think in leaps.&rdquo;
        </p>

        <p className="text-sm max-w-lg" style={{ color: '#64748b' }}>
          Pick any topic from the knowledge galaxy below. Each topic breaks down into
          analogy-first micro-lessons you can grasp in 2 minutes — then build with code,
          then share.
        </p>

        {/* Stats row */}
        {topics.length > 0 && (
          <div className="flex items-center gap-6 mt-6">
            <div className="text-center">
              <div className="text-2xl font-bold" style={{ color: '#8b5cf6' }}>
                {courseTopics.length}
              </div>
              <div className="text-xs" style={{ color: '#475569' }}>Course Modules</div>
            </div>
            <div className="w-px h-8" style={{ background: 'rgba(255,255,255,0.1)' }} />
            <div className="text-center">
              <div className="text-2xl font-bold" style={{ color: '#22d3ee' }}>
                {postTopics.length}
              </div>
              <div className="text-xs" style={{ color: '#475569' }}>Generated Posts</div>
            </div>
            <div className="w-px h-8" style={{ background: 'rgba(255,255,255,0.1)' }} />
            <div className="text-center">
              <div className="text-2xl font-bold" style={{ color: '#f1f5f9' }}>
                {topics.reduce((sum, t) => sum + (t.concepts?.length || 0), 0)}
              </div>
              <div className="text-xs" style={{ color: '#475569' }}>Concepts</div>
            </div>
          </div>
        )}
      </div>

      {/* Galaxy */}
      <div className="relative z-10 w-full max-w-5xl mx-auto px-4 sm:px-6">
        {kgData.nodes.length > 0 ? (
          <Suspense
            fallback={
              <div
                className="w-full rounded-2xl animate-pulse"
                style={{
                  height: 600,
                  background: 'rgba(139,92,246,0.05)',
                  border: '1px solid rgba(139,92,246,0.15)',
                }}
              />
            }
          >
            <TopicGalaxyWrapper data={kgData} />
          </Suspense>
        ) : (
          <div
            className="w-full rounded-2xl flex flex-col items-center justify-center text-center gap-4 px-8"
            style={{
              height: 480,
              background: 'rgba(139,92,246,0.03)',
              border: '1px solid rgba(139,92,246,0.15)',
            }}
          >
            <span className="text-5xl opacity-30">&#127759;</span>
            <p className="text-sm" style={{ color: '#64748b' }}>
              Knowledge graph is empty.
            </p>
            <p className="text-xs max-w-sm" style={{ color: '#475569' }}>
              Run{' '}
              <code
                className="px-1.5 py-0.5 rounded text-xs"
                style={{ background: 'rgba(255,255,255,0.08)', color: '#a78bfa' }}
              >
                uv run python scripts/ingest_courses.py
              </code>{' '}
              to populate course topics, then start the API:
            </p>
            <code
              className="px-3 py-1.5 rounded-lg text-xs"
              style={{ background: 'rgba(255,255,255,0.06)', color: '#94a3b8', border: '1px solid rgba(255,255,255,0.08)' }}
            >
              uv run python api_server.py
            </code>
          </div>
        )}

        {/* Instruction */}
        <p className="text-center text-xs mt-3" style={{ color: '#334155' }}>
          Click any topic node to begin &bull; Scroll to zoom &bull; Drag nodes to explore
        </p>
      </div>

      {/* CTA */}
      <div className="relative z-10 flex flex-col items-center gap-3 py-10">
        {firstTopic ? (
          <Link
            href={`/learn/${firstTopic.id}`}
            className="px-8 py-3 rounded-full font-semibold text-white transition-all duration-200 text-sm"
            style={{
              background: 'linear-gradient(135deg, #8b5cf6 0%, #22d3ee 100%)',
              boxShadow: '0 0 30px rgba(139,92,246,0.4)',
            }}
          >
            Start Learning &rarr;
          </Link>
        ) : (
          <p className="text-sm" style={{ color: '#475569' }}>
            Start the API server:{' '}
            <code
              className="px-2 py-0.5 rounded text-xs"
              style={{ background: 'rgba(255,255,255,0.06)', color: '#a78bfa' }}
            >
              uv run python api_server.py
            </code>
          </p>
        )}
      </div>

      {/* Topic pills */}
      {courseTopics.length > 0 && (
        <div
          className="relative z-10 w-full max-w-4xl mx-auto px-6 pb-16"
          style={{ borderTop: '1px solid rgba(139,92,246,0.08)', paddingTop: 32 }}
        >
          <p
            className="text-xs font-bold uppercase tracking-widest text-center mb-5"
            style={{ color: '#334155' }}
          >
            Browse all course modules
          </p>
          <div className="flex flex-wrap gap-2 justify-center">
            {courseTopics.map((t) => (
              <Link
                key={t.id}
                href={`/learn/${t.id}`}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs transition-all duration-200"
                style={{
                  border: '1px solid rgba(139,92,246,0.2)',
                  background: 'rgba(139,92,246,0.07)',
                  color: '#a78bfa',
                }}
              >
                {t.module_number && (
                  <span style={{ color: '#6b7280', fontFamily: 'monospace' }}>{t.module_number}</span>
                )}
                {t.name}
              </Link>
            ))}
            {postTopics.map((t) => (
              <Link
                key={t.id}
                href={`/learn/${t.id}`}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs transition-all duration-200"
                style={{
                  border: '1px solid rgba(34,211,238,0.2)',
                  background: 'rgba(34,211,238,0.06)',
                  color: '#67e8f9',
                }}
              >
                <span style={{ color: '#22d3ee' }}>&#10022;</span>
                {t.name}
              </Link>
            ))}
          </div>
        </div>
      )}
    </main>
  );
}
