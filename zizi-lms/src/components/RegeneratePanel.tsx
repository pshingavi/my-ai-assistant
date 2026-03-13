'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { fetchAnalogySuggestions, regenerateWithAnalogy } from '@/src/lib/api';
import type { CachedByte, P5Sketch } from '@/src/types';

interface RegeneratePanelProps {
  topicId: string;
  concept: string;
  currentAnalogy?: string;
  onClose: () => void;
  onComplete: (byte: CachedByte, sketch: P5Sketch) => void;
}

export default function RegeneratePanel({
  topicId,
  concept,
  currentAnalogy = '',
  onClose,
  onComplete,
}: RegeneratePanelProps) {
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(true);
  const [customAnalogy, setCustomAnalogy] = useState(currentAnalogy);
  const [regenerating, setRegenerating] = useState(false);
  const [selectedSuggestion, setSelectedSuggestion] = useState<number | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    setLoadingSuggestions(true);
    fetchAnalogySuggestions(topicId, concept)
      .then(setSuggestions)
      .catch(() => setSuggestions([]))
      .finally(() => setLoadingSuggestions(false));
  }, [topicId, concept]);

  const handleUse = async (analogy?: string) => {
    setRegenerating(true);
    setError('');
    try {
      const result = await regenerateWithAnalogy(topicId, concept, analogy);
      const sketch: P5Sketch = { sketch_code: result.sketch_code, steps: result.steps };
      onComplete(result.byte, sketch);
    } catch {
      setError('Regeneration failed — is the API server running?');
      setRegenerating(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
      className="overflow-hidden"
      style={{ borderTop: '1px solid rgba(124,58,237,0.15)' }}
    >
      <div
        className="relative p-6"
        style={{ background: 'rgba(124,58,237,0.03)' }}
      >
        {/* Loading overlay */}
        <AnimatePresence>
          {regenerating && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 flex flex-col items-center justify-center gap-3 z-10"
              style={{ background: 'rgba(15,10,46,0.92)', borderRadius: 12 }}
            >
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                className="w-10 h-10 rounded-full border-2"
                style={{ borderColor: 'rgba(124,58,237,0.2)', borderTopColor: '#7c3aed' }}
              />
              <p className="text-sm font-semibold" style={{ color: '#a78bfa' }}>
                Regenerating all assets…
              </p>
              <p className="text-xs" style={{ color: 'rgba(167,139,250,0.5)' }}>
                This takes ~30 seconds
              </p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2">
            <span style={{ fontSize: 18 }}>✨</span>
            <span
              className="text-xs font-black uppercase tracking-widest"
              style={{ color: 'var(--text-3)', letterSpacing: '0.12em' }}
            >
              Choose New Analogy
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-xs px-3 py-1.5 rounded-lg"
            style={{
              color: 'var(--text-4)',
              border: '1px solid var(--border)',
              background: 'transparent',
            }}
          >
            Cancel
          </button>
        </div>

        {/* Suggestions */}
        <div className="space-y-3 mb-5">
          {loadingSuggestions ? (
            <div className="space-y-3">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="rounded-xl p-4 animate-pulse"
                  style={{
                    background: 'rgba(124,58,237,0.06)',
                    border: '1px solid rgba(124,58,237,0.1)',
                    height: 72,
                  }}
                />
              ))}
            </div>
          ) : (
            suggestions.map((suggestion, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.08 }}
                className="flex items-start gap-3 rounded-xl p-4 cursor-pointer transition-all"
                style={{
                  background:
                    selectedSuggestion === i
                      ? 'rgba(124,58,237,0.12)'
                      : 'rgba(124,58,237,0.04)',
                  border:
                    selectedSuggestion === i
                      ? '1px solid rgba(124,58,237,0.4)'
                      : '1px solid rgba(124,58,237,0.12)',
                }}
                onClick={() =>
                  setSelectedSuggestion(selectedSuggestion === i ? null : i)
                }
              >
                <div
                  className="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold mt-0.5"
                  style={{
                    background:
                      selectedSuggestion === i
                        ? '#7c3aed'
                        : 'rgba(124,58,237,0.15)',
                    color: selectedSuggestion === i ? '#fff' : '#7c3aed',
                  }}
                >
                  {i + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <p
                    className="text-sm leading-relaxed"
                    style={{ color: 'var(--text-2)', lineHeight: 1.65 }}
                  >
                    {suggestion}
                  </p>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleUse(suggestion);
                  }}
                  className="flex-shrink-0 px-3 py-1.5 rounded-lg text-xs font-bold"
                  style={{
                    background: 'rgba(124,58,237,0.15)',
                    color: '#a78bfa',
                    border: '1px solid rgba(124,58,237,0.3)',
                  }}
                >
                  Use this
                </button>
              </motion.div>
            ))
          )}
        </div>

        {/* Divider */}
        <div className="flex items-center gap-3 mb-4">
          <div className="flex-1 h-px" style={{ background: 'var(--border)' }} />
          <span className="text-xs" style={{ color: 'var(--text-5)' }}>
            or write your own
          </span>
          <div className="flex-1 h-px" style={{ background: 'var(--border)' }} />
        </div>

        {/* Custom input */}
        <div className="flex gap-2">
          <input
            value={customAnalogy}
            onChange={(e) => setCustomAnalogy(e.target.value)}
            placeholder="e.g. Think of it like a GPS recalculating your route…"
            className="flex-1 rounded-xl px-4 py-3 text-sm outline-none"
            style={{
              background: 'var(--bg-2)',
              border: '1px solid var(--border-strong)',
              color: 'var(--text-1)',
            }}
            onFocus={(e) =>
              (e.target.style.borderColor = 'rgba(124,58,237,0.5)')
            }
            onBlur={(e) =>
              (e.target.style.borderColor = 'var(--border-strong)')
            }
            onKeyDown={(e) => {
              if (e.key === 'Enter' && customAnalogy.trim()) {
                handleUse(customAnalogy.trim());
              }
            }}
          />
          <button
            onClick={() => handleUse(customAnalogy.trim() || undefined)}
            disabled={!customAnalogy.trim() && selectedSuggestion === null}
            className="px-4 py-3 rounded-xl text-xs font-bold transition-all disabled:opacity-40"
            style={{
              background: 'linear-gradient(135deg, #7c3aed, #6d28d9)',
              color: '#fff',
              boxShadow: '0 2px 12px rgba(124,58,237,0.35)',
            }}
          >
            Generate
          </button>
        </div>

        {error && (
          <p className="text-xs mt-3" style={{ color: '#dc2626' }}>
            {error}
          </p>
        )}
      </div>
    </motion.div>
  );
}
