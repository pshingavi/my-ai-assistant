'use client';

import { useState, useMemo, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';
import { fetchAllQA, askQAQuestion } from '@/src/lib/api';
import type { TopicQA, QAPair } from '@/src/types';

interface Props {
  initialData: TopicQA[];
}

function SourceBadge({ source }: { source: string }) {
  const short = source.replace(/^AIE9_/, '').replace(/_/g, ' ').replace(/\.pdf$/i, '').replace(/\.ipynb$/i, '');
  return (
    <span
      style={{
        fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 20,
        background: 'rgba(124,58,237,0.08)', color: '#7c3aed',
        border: '1px solid rgba(124,58,237,0.15)', whiteSpace: 'nowrap',
      }}
    >
      {short}
    </span>
  );
}

function QACard({ pair, index }: { pair: QAPair; index: number }) {
  const [open, setOpen] = useState(false);
  return (
    <div
      style={{
        borderRadius: 14,
        border: `1px solid ${open ? 'rgba(124,58,237,0.25)' : 'var(--border)'}`,
        background: open ? 'rgba(124,58,237,0.03)' : 'var(--surface-2)',
        overflow: 'hidden',
        transition: 'border-color 0.2s, background 0.2s',
      }}
    >
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%', textAlign: 'left', padding: '14px 18px',
          display: 'flex', alignItems: 'flex-start', gap: 12,
          background: 'none', border: 'none', cursor: 'pointer',
        }}
      >
        <span style={{
          flexShrink: 0, width: 22, height: 22, borderRadius: 8,
          background: 'rgba(124,58,237,0.1)', color: '#7c3aed',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 10, fontWeight: 800, marginTop: 1,
        }}>
          {index + 1}
        </span>
        <span style={{ flex: 1, fontSize: 13.5, fontWeight: 600, color: 'var(--text-1)', lineHeight: 1.5, textAlign: 'left' }}>
          {pair.question}
        </span>
        <span style={{ flexShrink: 0, fontSize: 14, color: open ? '#7c3aed' : 'var(--text-4)', transition: 'transform 0.2s', transform: open ? 'rotate(180deg)' : 'none' }}>
          ▾
        </span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            style={{ overflow: 'hidden' }}
          >
            <div style={{ padding: '0 18px 16px 52px' }}>
              <p style={{ fontSize: 13, lineHeight: 1.8, color: 'var(--text-2)', marginBottom: 12 }}>
                {pair.answer}
              </p>
              {pair.sources.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {pair.sources.map(s => <SourceBadge key={s} source={s} />)}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function AskInput({ topicId, topicName }: { topicId: string; topicName: string }) {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [sources, setSources] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const handleAsk = async () => {
    if (!question.trim()) return;
    setLoading(true);
    setAnswer('');
    setSources([]);
    try {
      const res = await askQAQuestion(question, topicId, topicName);
      setAnswer(res.answer);
      setSources(res.sources);
    } catch {
      toast.error('Failed to get answer — is the API running?');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ marginTop: 24, borderRadius: 16, border: '1px solid rgba(124,58,237,0.2)', overflow: 'hidden', background: 'rgba(124,58,237,0.02)' }}>
      <div style={{ padding: '14px 16px', borderBottom: '1px solid rgba(124,58,237,0.1)' }}>
        <p style={{ fontSize: 11, fontWeight: 800, color: '#7c3aed', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
          ✦ Ask anything about {topicName}
        </p>
      </div>
      <div style={{ padding: 16 }}>
        <div style={{ display: 'flex', gap: 10 }}>
          <input
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAsk()}
            placeholder="e.g. How does cosine similarity affect retrieval quality?"
            style={{
              flex: 1, padding: '10px 14px', borderRadius: 10, fontSize: 13,
              border: '1px solid var(--border-strong)', background: 'var(--bg-1)',
              color: 'var(--text-1)', outline: 'none',
            }}
            onFocus={e => (e.target.style.borderColor = 'rgba(124,58,237,0.5)')}
            onBlur={e => (e.target.style.borderColor = 'var(--border-strong)')}
          />
          <button
            onClick={handleAsk}
            disabled={loading || !question.trim()}
            style={{
              padding: '10px 20px', borderRadius: 10, fontWeight: 700, fontSize: 13,
              background: loading ? 'rgba(124,58,237,0.3)' : '#7c3aed',
              color: '#fff', border: 'none', cursor: loading ? 'wait' : 'pointer',
              display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0,
            }}
          >
            {loading ? (
              <span style={{ width: 14, height: 14, borderRadius: '50%', border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', display: 'inline-block', animation: 'spin 0.8s linear infinite' }} />
            ) : '→'}
            {loading ? 'Thinking…' : 'Ask'}
          </button>
        </div>

        <AnimatePresence>
          {answer && (
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              style={{ marginTop: 14 }}
            >
              <p style={{ fontSize: 13, lineHeight: 1.8, color: 'var(--text-2)', marginBottom: 10 }}>{answer}</p>
              {sources.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {sources.map(s => <SourceBadge key={s} source={s} />)}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

export default function QAExplorer({ initialData }: Props) {
  const [search, setSearch] = useState('');
  const [selectedId, setSelectedId] = useState<string>(initialData[0]?.topic_id ?? '');

  // Filter sidebar topics by search
  const filteredTopics = useMemo(() => {
    const q = search.toLowerCase();
    if (!q) return initialData;
    return initialData.filter(t =>
      t.topic_name.toLowerCase().includes(q) ||
      t.qa_pairs.some(p => p.question.toLowerCase().includes(q) || p.answer.toLowerCase().includes(q))
    );
  }, [search, initialData]);

  const selectedTopic = useMemo(() => initialData.find(t => t.topic_id === selectedId), [selectedId, initialData]);

  // Filtered Q&A within selected topic
  const filteredPairs = useMemo(() => {
    if (!selectedTopic) return [];
    const q = search.toLowerCase();
    if (!q) return selectedTopic.qa_pairs;
    return selectedTopic.qa_pairs.filter(p =>
      p.question.toLowerCase().includes(q) || p.answer.toLowerCase().includes(q)
    );
  }, [selectedTopic, search]);

  // Group sidebar by module
  const grouped = useMemo(() => {
    const groups: Record<string, TopicQA[]> = {};
    for (const t of filteredTopics) {
      const key = t.topic_id?.startsWith('project-')
        ? '🏗️ Project Q&A'
        : t.module_number ? `Module ${t.module_number}` : 'Other';
      if (!groups[key]) groups[key] = [];
      groups[key].push(t);
    }
    return Object.entries(groups).sort(([a], [b]) => {
      if (a.startsWith('🏗️')) return -1;
      if (b.startsWith('🏗️')) return 1;
      return a.localeCompare(b);
    });
  }, [filteredTopics]);

  const totalQA = useMemo(() => initialData.reduce((sum, t) => sum + t.qa_pairs.length, 0), [initialData]);

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      {/* Sidebar */}
      <div style={{
        width: 260, flexShrink: 0, borderRight: '1px solid var(--border)',
        display: 'flex', flexDirection: 'column', background: 'var(--surface-2)',
        overflow: 'hidden',
      }}>
        {/* Search */}
        <div style={{ padding: '12px 14px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
          <div style={{ position: 'relative' }}>
            <span style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', fontSize: 13, color: 'var(--text-4)' }}>🔍</span>
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search topics or Q&A…"
              style={{
                width: '100%', padding: '8px 10px 8px 32px', borderRadius: 10, fontSize: 12,
                border: '1px solid var(--border-strong)', background: 'var(--bg-1)',
                color: 'var(--text-1)', outline: 'none', boxSizing: 'border-box',
              }}
            />
          </div>
          <p style={{ fontSize: 10, color: 'var(--text-5)', marginTop: 8, textAlign: 'center' }}>
            {initialData.length} topics · {totalQA} Q&A pairs
          </p>
        </div>

        {/* Topic list */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '8px 0' }}>
          {grouped.length === 0 && (
            <p style={{ padding: '20px 16px', fontSize: 12, color: 'var(--text-4)', textAlign: 'center' }}>No matches</p>
          )}
          {grouped.map(([module, topics]) => (
            <div key={module}>
              <div style={{ padding: '8px 16px 4px', fontSize: 9, fontWeight: 800, color: 'var(--text-5)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                {module}
              </div>
              {topics.map(t => {
                const active = t.topic_id === selectedId;
                return (
                  <button
                    key={t.topic_id}
                    onClick={() => setSelectedId(t.topic_id)}
                    style={{
                      width: '100%', textAlign: 'left', padding: '8px 16px',
                      background: active ? 'rgba(124,58,237,0.1)' : 'none',
                      border: 'none', cursor: 'pointer',
                      borderLeft: active ? '3px solid #7c3aed' : '3px solid transparent',
                      transition: 'all 0.15s',
                    }}
                    onMouseEnter={e => { if (!active) (e.currentTarget as HTMLElement).style.background = 'rgba(124,58,237,0.04)'; }}
                    onMouseLeave={e => { if (!active) (e.currentTarget as HTMLElement).style.background = 'none'; }}
                  >
                    <div style={{ fontSize: 12, fontWeight: active ? 700 : 500, color: active ? '#7c3aed' : 'var(--text-2)', lineHeight: 1.3 }}>
                      {t.topic_name}
                    </div>
                    <div style={{ fontSize: 10, color: 'var(--text-5)', marginTop: 2 }}>
                      {t.qa_pairs.length} Q&A
                    </div>
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Main content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '24px 32px' }}>
        {!selectedTopic ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-4)', fontSize: 14 }}>
            Select a topic from the sidebar
          </div>
        ) : (
          <div style={{ maxWidth: 780 }}>
            {/* Topic header */}
            <div style={{ marginBottom: 24 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                {selectedTopic.module_number && (
                  <span style={{
                    fontSize: 10, fontWeight: 800, padding: '3px 10px', borderRadius: 20,
                    background: 'rgba(124,58,237,0.1)', color: '#7c3aed',
                    letterSpacing: '0.08em', textTransform: 'uppercase',
                  }}>
                    {selectedTopic.topic_id?.startsWith('project-') ? 'Project' : `Module ${selectedTopic.module_number}`}
                  </span>
                )}
                <span style={{ fontSize: 10, color: 'var(--text-4)', fontWeight: 600 }}>
                  {filteredPairs.length} of {selectedTopic.qa_pairs.length} Q&A shown
                </span>
              </div>
              <h2 style={{ fontSize: 22, fontWeight: 800, color: 'var(--text-1)', margin: 0 }}>
                {selectedTopic.topic_name}
              </h2>
            </div>

            {/* Q&A cards */}
            {filteredPairs.length === 0 ? (
              <p style={{ color: 'var(--text-4)', fontSize: 13 }}>No Q&A matches your search.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {filteredPairs.map((pair, i) => (
                  <QACard key={i} pair={pair} index={i} />
                ))}
              </div>
            )}

            {/* Ask input */}
            <AskInput topicId={selectedTopic.topic_id} topicName={selectedTopic.topic_name} />
          </div>
        )}
      </div>
    </div>
  );
}
