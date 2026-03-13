'use client';

import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import type { TopicSummary } from '@/src/types';

interface Props {
  topics: TopicSummary[];
  currentTopicId: string;
  currentConcept?: string;
  open: boolean;
  onClose: () => void;
  onConceptSelect?: (topicId: string, conceptIndex: number) => void;
}

export default function TopicDrawer({ topics, currentTopicId, currentConcept, open, onClose, onConceptSelect }: Props) {
  const courseTopics = topics
    .filter(t => !t.is_post)
    .sort((a, b) => parseInt(a.module_number || '99') - parseInt(b.module_number || '99'));
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
            style={{ background: 'rgba(30,27,75,0.2)', backdropFilter: 'blur(6px)' }}
          />

          {/* Drawer panel */}
          <motion.div
            initial={{ x: '-100%' }}
            animate={{ x: 0 }}
            exit={{ x: '-100%' }}
            transition={{ type: 'spring', damping: 26, stiffness: 220 }}
            className="fixed left-0 top-0 bottom-0 z-50 flex flex-col"
            style={{
              width: 288,
              background: 'var(--surface-2)',
              borderRight: '1px solid var(--border)',
              backdropFilter: 'blur(20px)',
              boxShadow: '4px 0 40px rgba(124,58,237,0.12)',
            }}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4"
              style={{ borderBottom: '1px solid var(--border)' }}>
              <div className="flex items-center gap-2">
                <span className="text-xl">⚡</span>
                <span className="font-bold text-sm" style={{ color: '#7c3aed' }}>Zizi Byte</span>
              </div>
              <motion.button
                onClick={onClose}
                whileHover={{ scale: 1.1, rotate: 90 }}
                whileTap={{ scale: 0.9 }}
                className="text-xs p-1.5 rounded-lg"
                style={{ color: '#7c6fa0', background: 'rgba(124,58,237,0.06)' }}
              >✕</motion.button>
            </div>

            {/* Topic list */}
            <div className="flex-1 overflow-y-auto py-3 px-3 space-y-0.5">
              {courseTopics.length > 0 && (
                <>
                  <p className="text-xs font-bold uppercase tracking-widest px-3 py-2"
                    style={{ color: '#c4b5fd', letterSpacing: '0.14em' }}>
                    Course Modules
                  </p>
                  {courseTopics.map(t => (
                    <div key={t.id}>
                      <Link href={`/learn/${t.id}`} onClick={t.id === currentTopicId ? (e) => e.preventDefault() : onClose}>
                        <motion.div
                          whileHover={{ x: t.id === currentTopicId ? 0 : 3 }}
                          className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl transition-all duration-150"
                          style={t.id === currentTopicId
                            ? { background: 'rgba(124,58,237,0.1)', border: '1px solid rgba(124,58,237,0.2)' }
                            : { border: '1px solid transparent' }}
                        >
                          {t.module_number && (
                            <span className="text-xs font-mono font-bold shrink-0 w-7 text-center px-1 py-0.5 rounded-md"
                              style={{
                                background: t.id === currentTopicId ? '#7c3aed' : 'rgba(124,58,237,0.08)',
                                color: t.id === currentTopicId ? '#fff' : '#7c3aed',
                                fontSize: 10,
                              }}>
                              {t.module_number}
                            </span>
                          )}
                          <span className="text-sm truncate font-medium"
                            style={{ color: t.id === currentTopicId ? 'var(--text-1)' : 'var(--text-3)' }}>
                            {t.name}
                          </span>
                        </motion.div>
                      </Link>

                      {/* Concept sub-list for current topic */}
                      {t.id === currentTopicId && t.concepts.length > 1 && (
                        <div className="ml-4 mt-0.5 mb-1 space-y-0.5 border-l pl-3" style={{ borderColor: 'rgba(124,58,237,0.2)' }}>
                          {t.concepts.map((c, idx) => (
                            <button
                              key={idx}
                              onClick={() => { onConceptSelect?.(t.id, idx); onClose(); }}
                              className="w-full text-left px-2 py-1.5 rounded-lg text-xs font-medium transition-all duration-100"
                              style={c === currentConcept
                                ? { background: 'rgba(124,58,237,0.12)', color: '#7c3aed' }
                                : { color: 'var(--text-4)' }}
                            >
                              {c}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </>
              )}

              {postTopics.length > 0 && (
                <>
                  <p className="text-xs font-bold uppercase tracking-widest px-3 py-2 mt-3"
                    style={{ color: '#c4b5fd', letterSpacing: '0.14em' }}>
                    Generated Posts
                  </p>
                  {postTopics.map(t => (
                    <Link key={t.id} href={`/learn/${t.id}`} onClick={onClose}>
                      <motion.div
                        whileHover={{ x: 3 }}
                        className="flex items-center gap-2 px-3 py-2.5 rounded-xl transition-all duration-150"
                        style={t.id === currentTopicId
                          ? { background: 'rgba(8,145,178,0.07)', border: '1px solid rgba(8,145,178,0.18)' }
                          : { border: '1px solid transparent' }}
                      >
                        <span style={{ color: '#0891b2', fontSize: 10 }}>✶</span>
                        <span className="text-sm truncate font-medium"
                          style={{ color: t.id === currentTopicId ? '#0e7490' : 'var(--text-3)' }}>
                          {t.name}
                        </span>
                      </motion.div>
                    </Link>
                  ))}
                </>
              )}
            </div>

            {/* Footer */}
            <div className="px-5 py-4" style={{ borderTop: '1px solid var(--border)' }}>
              <p className="text-xs text-center italic font-medium" style={{ color: '#c4b5fd' }}>
                Learn in bytes. Think in leaps.
              </p>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
