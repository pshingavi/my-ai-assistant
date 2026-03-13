'use client';

import { useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import dynamic from 'next/dynamic';
import type { P5Step } from '@/src/types';
import { fetchClaudeInteraction, downloadNotebook } from '@/src/lib/api';

const InteractivePlayer = dynamic(() => import('./InteractivePlayer'), { ssr: false });

interface BuildCardProps {
  topicId: string;
  concept: string;
  topicName: string;
}

interface InteractiveSketch {
  sketch_code: string;
  steps: P5Step[];
}

function CodePanel({ step }: { step: P5Step }) {
  return (
    <motion.div
      key={step.step_index}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -16 }}
      transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
    >
      <div className="flex items-center justify-between mb-4">
        <div>
          <p className="text-xs font-black uppercase tracking-widest"
            style={{ color: 'var(--accent)', letterSpacing: '0.12em' }}>
            Step {step.step_index + 1} — {step.title}
          </p>
          <p className="text-sm mt-1 leading-relaxed" style={{ color: 'var(--text-3)' }}>
            {step.description}
          </p>
        </div>
      </div>

      <div className="rounded-2xl overflow-hidden mb-4"
        style={{
          background: '#0a0a18',
          border: '1px solid rgba(139,92,246,0.2)',
          boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
        }}
      >
        <div className="flex items-center justify-between px-5 py-3.5"
          style={{ background: 'rgba(139,92,246,0.07)', borderBottom: '1px solid rgba(139,92,246,0.14)' }}>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5">
              {['#ff5f57', '#febc2e', '#28c840'].map((c, i) => (
                <span key={i} style={{ width: 10, height: 10, borderRadius: '50%', background: c, opacity: 0.75, display: 'inline-block' }} />
              ))}
            </div>
            <span className="text-xs font-mono ml-3" style={{ color: 'rgba(255,255,255,0.3)' }}>
              {step.language || 'python'}
            </span>
          </div>
          <span className="px-3 py-1 rounded-full text-xs font-bold"
            style={{ background: 'rgba(139,92,246,0.2)', color: '#a78bfa', border: '1px solid rgba(139,92,246,0.3)' }}>
            {step.language || 'python'}
          </span>
        </div>
        <pre className="overflow-x-auto"
          style={{ padding: '20px 24px 24px', color: '#e2e8f0', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', lineHeight: 1.8, fontSize: 13.5 }}>
          <code>{step.code_snippet}</code>
        </pre>
      </div>

      {step.explanation && (
        <div className="rounded-xl px-5 py-4"
          style={{ background: 'var(--accent-soft)', border: '1px solid var(--border)' }}>
          <p className="text-sm leading-relaxed" style={{ color: 'var(--text-2)', lineHeight: 1.75 }}>
            <span className="font-semibold" style={{ color: 'var(--accent)' }}>Explanation: </span>
            {step.explanation}
          </p>
        </div>
      )}
    </motion.div>
  );
}

export default function BuildCard({ topicId, concept, topicName }: BuildCardProps) {
  const [sketch, setSketch] = useState<InteractiveSketch | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [currentStep, setCurrentStep] = useState(0);

  const loadSketch = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const result = await fetchClaudeInteraction(topicId, concept);
      setSketch(result);
    } catch {
      setError('Failed to load interactive widget — is the API server running?');
    } finally {
      setLoading(false);
    }
  }, [topicId, concept]);

  useEffect(() => {
    loadSketch();
  }, [loadSketch]);

  // Listen for step changes from the iframe
  useEffect(() => {
    const handler = (event: MessageEvent) => {
      if (event.data?.type === 'step' && typeof event.data.index === 'number') {
        setCurrentStep(event.data.index);
      }
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, []);

  const steps = sketch?.steps ?? [];
  const currentStepData = steps[currentStep] ?? null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -16 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
      className="rounded-3xl overflow-hidden"
      style={{ boxShadow: 'var(--shadow-lg)' }}
    >
      {/* Header */}
      <div className="px-8 py-6 flex items-center gap-5"
        style={{ background: 'linear-gradient(135deg, var(--bg) 0%, var(--surface) 100%)', borderBottom: '1px solid var(--border)' }}>
        <div className="w-14 h-14 rounded-2xl flex items-center justify-center text-2xl flex-shrink-0"
          style={{ background: 'var(--accent-soft)', border: '1px solid var(--border)' }}>
          🏗️
        </div>
        <div className="flex-1 min-w-0">
          <h2 className="text-xl font-extrabold leading-tight truncate" style={{ color: 'var(--text-1)' }}>
            {concept}
          </h2>
          <p className="text-xs mt-1.5" style={{ color: 'var(--text-4)' }}>
            {topicName} · Build Mode
          </p>
        </div>
        <motion.button
          onClick={() => downloadNotebook(topicId, concept)}
          whileHover={{ scale: 1.04 }}
          whileTap={{ scale: 0.96 }}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold flex-shrink-0"
          style={{ background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.25)', color: '#34d399' }}
        >
          <span>📓</span>
          Notebook
        </motion.button>
      </div>

      <div style={{ background: 'var(--surface)' }}>
        {error && (
          <div className="m-6 rounded-2xl p-8 text-sm text-center"
            style={{ background: 'rgba(220,38,38,0.04)', border: '1px solid rgba(220,38,38,0.12)', color: '#dc2626' }}>
            {error}
            <button onClick={loadSketch} className="mt-4 block mx-auto px-4 py-2 rounded-xl text-xs font-semibold"
              style={{ background: 'rgba(220,38,38,0.08)', border: '1px solid rgba(220,38,38,0.15)', color: '#dc2626' }}>
              Retry
            </button>
          </div>
        )}

        {loading && (
          <div className="flex flex-col items-center justify-center gap-4 py-24">
            <motion.div animate={{ rotate: 360 }} transition={{ duration: 1.2, repeat: Infinity, ease: 'linear' }}
              className="w-10 h-10 rounded-full border-2"
              style={{ borderColor: 'var(--border)', borderTopColor: 'var(--accent)' }} />
            <p className="text-sm font-medium" style={{ color: 'var(--text-3)' }}>
              Zizi Byte is preparing your interactive widget…
            </p>
          </div>
        )}

        {sketch && !loading && (
          <div className="p-6 space-y-5">
            <InteractivePlayer
              sketchCode={sketch.sketch_code}
              steps={sketch.steps}
              onStepChange={setCurrentStep}
            />

            <AnimatePresence mode="wait">
              {currentStepData && (
                <CodePanel key={`step-${currentStepData.step_index}`} step={currentStepData} />
              )}
            </AnimatePresence>

            <div className="flex justify-end pt-2">
              <motion.button
                onClick={() => downloadNotebook(topicId, concept)}
                whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.96 }}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold"
                style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)', color: '#34d399' }}
              >
                <span>📓</span>
                Download Full Notebook
              </motion.button>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}
