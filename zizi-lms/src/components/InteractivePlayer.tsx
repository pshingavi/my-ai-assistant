'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import type { P5Step } from '@/src/types';

interface InteractivePlayerProps {
  sketchCode: string;
  steps: P5Step[];
  onStepChange?: (index: number) => void;
  height?: number;
}

export default function InteractivePlayer({
  sketchCode, steps, onStepChange, height = 520,
}: InteractivePlayerProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => { setLoaded(false); setCurrentStep(0); }, [sketchCode]);

  const handleMessage = useCallback((e: MessageEvent) => {
    if (e.data?.type === 'step') {
      const idx = Number(e.data.index);
      if (!isNaN(idx) && idx >= 0) {
        setCurrentStep(idx);
        onStepChange?.(idx);
      }
    }
  }, [onStepChange]);

  useEffect(() => {
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [handleMessage]);

  return (
    <div className="relative w-full rounded-2xl overflow-hidden"
      style={{
        height,
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        boxShadow: 'var(--shadow-md)',
      }}
    >
      {!loaded && (
        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3"
          style={{ background: 'var(--surface)' }}>
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1.1, repeat: Infinity, ease: 'linear' }}
            className="w-9 h-9 rounded-full border-2"
            style={{ borderColor: 'var(--border)', borderTopColor: 'var(--accent)' }}
          />
          <p className="text-xs font-medium" style={{ color: 'var(--text-4)' }}>
            Zizi Byte is preparing your interactive widget…
          </p>
        </div>
      )}
      <iframe
        key={sketchCode.slice(0, 40)}
        srcDoc={sketchCode.replace(
          '</style>',
          `/* === ZiziByte theme overrides === */
body,#visual{background:#f5f3ff!important}
#panel{background:#faf9ff!important;border-top:1px solid rgba(124,58,237,0.18)!important}
#step-title{color:#4c1d95!important}
#step-desc{color:#374151!important}
#badge{background:rgba(124,58,237,0.1)!important;color:#7c3aed!important}
#prev{background:rgba(124,58,237,0.08)!important;color:#7c3aed!important;border:1px solid rgba(124,58,237,0.2)!important}
#next{background:#7c3aed!important;color:#fff!important}
.dot{background:rgba(124,58,237,0.15)!important}.dot.on{background:#7c3aed!important}
</style>`
        )}
        sandbox="allow-scripts"
        style={{
          width: '100%', height: '100%', border: 'none', display: 'block',
          opacity: loaded ? 1 : 0, transition: 'opacity 0.35s ease',
        }}
        onLoad={() => setLoaded(true)}
        title="Zizi interactive widget"
      />
    </div>
  );
}
