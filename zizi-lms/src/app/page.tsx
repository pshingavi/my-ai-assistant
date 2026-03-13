'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { fetchTopics } from '@/src/lib/api';
import type { TopicSummary } from '@/src/types';
import { useLMSStore } from '@/src/store/lmsStore';
import LearningRoadmap from '@/src/components/LearningRoadmap';

const MODULE_EMOJIS: Record<string, string> = {
  '01': '🧠', '02': '🔍', '03': '🤖', '04': '📚', '05': '🕸️',
  '06': '💾', '07': '🚀', '08': '🔬', '09': '🧪', '10': '📊',
  '11': '⚡', '14': '🔌', '15': '🛰️', '16': '🖥️', '17': '🤝', '18': '🛡️',
};

function TopicCard({ topic, index }: { topic: TopicSummary; index: number }) {
  const emoji = MODULE_EMOJIS[topic.module_number] ?? '📘';
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04, duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
    >
      <Link href={`/learn/${topic.id}`} className="block group h-full">
        <div
          className="h-full rounded-2xl transition-all duration-250 group-hover:scale-[1.025] group-hover:-translate-y-1"
          style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            boxShadow: 'var(--shadow-sm)',
            padding: '22px 20px 20px',
          }}
          onMouseEnter={e => {
            (e.currentTarget as HTMLElement).style.borderColor = 'rgba(124,58,237,0.35)';
            (e.currentTarget as HTMLElement).style.boxShadow = '0 12px 40px rgba(124,58,237,0.14), 0 4px 12px rgba(124,58,237,0.08)';
          }}
          onMouseLeave={e => {
            (e.currentTarget as HTMLElement).style.borderColor = 'var(--border)';
            (e.currentTarget as HTMLElement).style.boxShadow = 'var(--shadow-sm)';
          }}
        >
          <div className="flex items-start justify-between mb-4">
            <span style={{ fontSize: 32, lineHeight: 1 }}>{emoji}</span>
            {topic.module_number && (
              <span className="text-xs font-bold px-2.5 py-1 rounded-full font-mono"
                style={{ background: 'rgba(124,58,237,0.08)', color: '#7c3aed', border: '1px solid rgba(124,58,237,0.18)' }}>
                {topic.module_number}
              </span>
            )}
          </div>
          <h3 className="font-bold mb-2.5 leading-snug" style={{ color: 'var(--text-1)', fontSize: 14.5 }}>
            {topic.name}
          </h3>
          <p className="leading-relaxed mb-5" style={{ color: 'var(--text-4)', fontSize: 12.5, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden', lineHeight: 1.6 } as React.CSSProperties}>
            {topic.description}
          </p>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold flex items-center gap-1.5" style={{ color: 'var(--text-5)' }}>
              <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--accent)', display: 'inline-block', opacity: 0.7 }} />
              {topic.concepts.length} concepts
            </span>
            <span className="text-xs font-bold opacity-0 group-hover:opacity-100 transition-opacity duration-200"
              style={{ color: 'var(--accent)' }}>
              Start →
            </span>
          </div>
        </div>
      </Link>
    </motion.div>
  );
}

export default function HomePage() {
  const [topics, setTopics] = useState<TopicSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<'grid' | 'galaxy'>('grid');
  const visitedTopicIds = useLMSStore(s => s.visitedTopicIds);
  const resetProgress = useLMSStore(s => s.resetProgress);

  useEffect(() => {
    fetchTopics()
      .catch(() => [] as TopicSummary[])
      .then(t => { setTopics(t); setLoading(false); });
  }, []);

  const courseTopics = topics.filter(t => !t.is_post && !!t.module_number);
  const postTopics = topics.filter(t => t.is_post);
  const totalConcepts = courseTopics.reduce((s, t) => s + (t.concepts?.length || 0), 0);
  const firstTopic = courseTopics[0];

  return (
    <main className="min-h-screen flex flex-col pt-14" style={{ background: 'var(--bg)' }}>

      {/* ── Ambient background ── */}
      <div className="fixed inset-0 pointer-events-none" aria-hidden="true" style={{ zIndex: 0 }}>
        <div className="absolute -top-40 left-1/3 w-[600px] h-[600px] rounded-full opacity-[0.07]"
          style={{ background: 'radial-gradient(circle, var(--accent), transparent 70%)', filter: 'blur(80px)' }} />
        <div className="absolute bottom-0 right-0 w-[500px] h-[500px] rounded-full opacity-[0.05]"
          style={{ background: 'radial-gradient(circle, #06b6d4, transparent 70%)', filter: 'blur(80px)' }} />
      </div>

      {/* ── Hero ── */}
      <section className="relative z-10 flex flex-col items-center text-center pt-20 pb-16 px-6">
        <motion.div
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-2 text-xs font-semibold mb-7 rounded-full px-4 py-2"
          style={{ background: 'var(--accent-soft)', color: 'var(--text-5)', border: '1px solid rgba(124,58,237,0.2)' }}
        >
          ✨ Adaptive AI Micro-Learning — AIE9 Course
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.5 }}
          className="text-5xl sm:text-6xl lg:text-7xl font-extrabold mb-5 tracking-tight"
          style={{ color: 'var(--text-1)', lineHeight: 1.1 }}
        >
          Zizi{' '}
          <span style={{
            background: 'linear-gradient(135deg, #7c3aed 0%, #a855f7 50%, #06b6d4 100%)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          }}>
            Byte
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="text-xl sm:text-2xl font-light mb-4"
          style={{ color: 'var(--text-3)', fontStyle: 'italic' }}
        >
          &ldquo;Learn in bytes. Think in leaps.&rdquo;
        </motion.p>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.25 }}
          className="text-base max-w-xl leading-loose mb-12"
          style={{ color: 'var(--text-4)' }}
        >
          Each module breaks down into analogy-first micro-lessons you can grasp in 2&nbsp;minutes —
          then build with real code, then share with the world.
        </motion.p>

        {/* Stats */}
        {!loading && courseTopics.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="flex items-center gap-10 mb-12"
          >
            {[
              { value: courseTopics.length, label: 'Modules', icon: '📚' },
              { value: totalConcepts, label: 'Concepts', icon: '🧠' },
              { value: '3', label: 'Learning Modes', icon: '🚀' },
            ].map((s, i) => (
              <div key={i} className="text-center">
                <div className="text-4xl font-extrabold mb-1.5"
                  style={{ background: 'linear-gradient(135deg, #7c3aed, #a855f7)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                  {s.value}
                </div>
                <div className="text-xs font-semibold uppercase tracking-widest" style={{ color: 'var(--text-4)', letterSpacing: '0.1em' }}>{s.label}</div>
              </div>
            ))}
          </motion.div>
        )}

        {/* CTA */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35 }}
          className="flex items-center gap-3"
        >
          {!loading && firstTopic && (
            <Link href={`/learn/${firstTopic.id}`}
              className="px-8 py-3.5 rounded-2xl font-bold text-white text-sm transition-all duration-200 hover:scale-105 hover:shadow-xl"
              style={{
                background: 'linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%)',
                boxShadow: '0 4px 24px rgba(124,58,237,0.4)',
              }}>
              Start Learning →
            </Link>
          )}
          <Link href="/chat"
            className="px-6 py-3.5 rounded-2xl font-semibold text-sm transition-all duration-200 hover:scale-105"
            style={{
              background: 'var(--surface)',
              border: '1px solid var(--border-strong)',
              color: 'var(--text-2)',
              boxShadow: 'var(--shadow-sm)',
            }}>
            Ask AI →
          </Link>
        </motion.div>
      </section>

      {/* ── View toggle ── */}
      <div className="relative z-10 flex justify-center mb-8">
        <div className="flex items-center gap-1 p-1 rounded-xl"
          style={{ background: 'var(--surface)', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)' }}>
          {(['grid', 'galaxy'] as const).map(v => (
            <button
              key={v}
              onClick={() => setView(v)}
              className="px-4 py-2 rounded-lg text-xs font-semibold transition-all duration-200 capitalize"
              style={view === v
                ? { background: 'var(--accent)', color: '#fff', boxShadow: '0 2px 8px rgba(124,58,237,0.3)' }
                : { color: 'var(--text-3)' }}
            >
              {v === 'grid' ? '⊞ Grid' : '🗺️ Roadmap'}
            </button>
          ))}
        </div>
      </div>

      {/* ── Grid view ── */}
      {view === 'grid' && (
        <section className="relative z-10 w-full max-w-6xl mx-auto px-6 pb-20">
          {loading ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-5">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="rounded-2xl h-40 shimmer" style={{ border: '1px solid var(--border)' }} />
              ))}
            </div>
          ) : courseTopics.length > 0 ? (
            <>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-5 mb-12">
                {courseTopics.map((t, i) => <TopicCard key={t.id} topic={t} index={i} />)}
              </div>
              {postTopics.length > 0 && (
                <div>
                  <p className="text-xs font-bold uppercase tracking-widest mb-4 text-center"
                    style={{ color: 'var(--text-4)', letterSpacing: '0.15em' }}>
                    Generated Content Posts
                  </p>
                  <div className="flex flex-wrap gap-2 justify-center">
                    {postTopics.map(t => (
                      <Link key={t.id} href={`/learn/${t.id}`}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs transition-all hover:scale-105"
                        style={{ border: '1px solid var(--border-strong)', background: 'var(--surface)', color: 'var(--text-3)' }}>
                        <span style={{ color: 'var(--accent)' }}>✶</span>
                        {t.name}
                      </Link>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="w-full rounded-2xl flex flex-col items-center justify-center text-center gap-4 px-8 py-20"
              style={{ background: 'var(--accent-soft)', border: '1px solid var(--border)' }}>
              <span className="text-5xl opacity-30">🌏</span>
              <p className="text-sm" style={{ color: 'var(--text-3)' }}>Knowledge graph is empty.</p>
              <code className="px-3 py-1.5 rounded-lg text-xs"
                style={{ background: 'var(--surface)', color: 'var(--text-3)', border: '1px solid var(--border)' }}>
                uv run python scripts/ingest_courses.py
              </code>
            </div>
          )}
        </section>
      )}

      {/* ── Roadmap view ── */}
      {view === 'galaxy' && (
        <section className="relative z-0 w-full">
          {loading ? (
            <div className="w-full rounded-2xl shimmer mx-auto max-w-5xl" style={{ height: 600, border: '1px solid var(--border)' }} />
          ) : topics.filter(t => !t.is_post && !!t.module_number).length > 0 ? (
            <LearningRoadmap
              topics={topics}
              visitedTopicIds={visitedTopicIds}
              onReset={resetProgress}
            />
          ) : (
            <div className="w-full max-w-5xl mx-auto rounded-2xl flex flex-col items-center justify-center text-center gap-4 px-8 py-20"
              style={{ background: 'var(--accent-soft)', border: '1px solid var(--border)' }}>
              <span className="text-5xl opacity-30">🗺️</span>
              <p className="text-sm" style={{ color: 'var(--text-3)' }}>No topics yet. Run the ingestion script.</p>
            </div>
          )}
        </section>
      )}
    </main>
  );
}
