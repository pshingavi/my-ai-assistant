'use client';

import { motion } from 'framer-motion';
import clsx from 'clsx';

interface ConceptDotsProps {
  concepts: string[];
  currentIndex: number;
  onSelect: (index: number) => void;
}

export default function ConceptDots({ concepts, currentIndex, onSelect }: ConceptDotsProps) {
  return (
    <div className="flex flex-col gap-3 w-full">
      {/* Dot progress bar */}
      <div className="flex items-center gap-2 flex-wrap">
        {concepts.map((concept, i) => (
          <button
            key={i}
            onClick={() => onSelect(i)}
            title={concept}
            className="relative group flex items-center"
          >
            <motion.div
              animate={{
                width: i === currentIndex ? 24 : 10,
                background: i === currentIndex
                  ? '#8b5cf6'
                  : i < currentIndex
                  ? 'rgba(139,92,246,0.5)'
                  : 'rgba(255,255,255,0.15)',
              }}
              transition={{ duration: 0.25, ease: 'easeOut' }}
              className="h-2.5 rounded-full cursor-pointer"
              style={{ minWidth: 10 }}
            />
            {/* Tooltip */}
            <div
              className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 rounded-md text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10"
              style={{ background: '#1a1a24', border: '1px solid rgba(139,92,246,0.3)', color: '#f1f5f9', maxWidth: 180 }}
            >
              {concept}
            </div>
          </button>
        ))}
      </div>

      {/* Current concept label */}
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium" style={{ color: '#64748b' }}>
          Concept {currentIndex + 1} of {concepts.length}
        </span>
        <span className="text-sm font-semibold" style={{ color: '#8b5cf6' }}>
          {concepts[currentIndex]}
        </span>
      </div>
    </div>
  );
}
