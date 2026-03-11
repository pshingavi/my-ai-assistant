'use client';

import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import type { TopicSummary } from '@/src/types';

interface Props {
  topics: TopicSummary[];
  currentTopicId: string;
  open: boolean;
  onClose: () => void;
}

export default function TopicDrawer({ topics, currentTopicId, open, onClose }: Props) {
  const courseTopics = topics.filter(t => !t.is_post);
  const postTopics = topics.filter(t => t.is_post);

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-40"
            style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}
          />

          {/* Drawer panel */}
          <motion.div
            initial={{ x: '-100%' }}
            animate={{ x: 0 }}
            exit={{ x: '-100%' }}
            transition={{ type: 'spring', damping: 24, stiffness: 200 }}
            className="fixed left-0 top-0 bottom-0 z-50 flex flex-col"
            style={{
              width: 280,
              background: 'rgba(7,7,13,0.97)',
              borderRight: '1px solid rgba(139,92,246,0.15)',
              backdropFilter: 'blur(20px)',
            }}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4"
              style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
              <div className="flex items-center gap-2">
                <span className="text-lg">⚡</span>
                <span className="font-bold text-sm" style={{ color: '#8b5cf6' }}>Topics</span>
              </div>
              <button onClick={onClose} className="text-sm p-1" style={{ color: '#475569' }}>✕</button>
            </div>

            {/* Topic list */}
            <div className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
              {courseTopics.length > 0 && (
                <>
                  <p className="text-xs font-bold uppercase tracking-widest px-2 mb-3"
                    style={{ color: '#334155', letterSpacing: '0.15em' }}>Course Modules</p>
                  {courseTopics.map(t => (
                    <Link key={t.id} href={`/learn/${t.id}`} onClick={onClose}>
                      <div className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl transition-all duration-150"
                        style={t.id === currentTopicId
                          ? { background: 'rgba(139,92,246,0.18)', border: '1px solid rgba(139,92,246,0.3)' }
                          : { border: '1px solid transparent' }}>
                        {t.module_number && (
                          <span className="text-xs font-mono shrink-0 w-8 text-center px-1 py-0.5 rounded"
                            style={{ background: 'rgba(139,92,246,0.15)', color: '#8b5cf6', fontSize: 10 }}>
                            {t.module_number}
                          </span>
                        )}
                        <span className="text-sm truncate" style={{ color: t.id === currentTopicId ? '#e2e8f0' : '#94a3b8' }}>
                          {t.name}
                        </span>
                      </div>
                    </Link>
                  ))}
                </>
              )}

              {postTopics.length > 0 && (
                <>
                  <p className="text-xs font-bold uppercase tracking-widest px-2 mb-3 mt-5"
                    style={{ color: '#334155', letterSpacing: '0.15em' }}>Generated Posts</p>
                  {postTopics.map(t => (
                    <Link key={t.id} href={`/learn/${t.id}`} onClick={onClose}>
                      <div className="flex items-center gap-2 px-3 py-2.5 rounded-xl transition-all duration-150"
                        style={t.id === currentTopicId
                          ? { background: 'rgba(34,211,238,0.1)', border: '1px solid rgba(34,211,238,0.25)' }
                          : { border: '1px solid transparent' }}>
                        <span style={{ color: '#22d3ee', fontSize: 10 }}>✶</span>
                        <span className="text-sm truncate" style={{ color: t.id === currentTopicId ? '#67e8f9' : '#64748b' }}>
                          {t.name}
                        </span>
                      </div>
                    </Link>
                  ))}
                </>
              )}
            </div>

            {/* Footer */}
            <div className="px-5 py-4" style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
              <p className="text-xs text-center italic" style={{ color: '#1e293b' }}>
                Learn in bytes. Think in leaps.
              </p>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
