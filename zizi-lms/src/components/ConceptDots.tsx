'use client';

import { motion } from 'framer-motion';

interface ConceptDotsProps {
  concepts: string[];
  currentIndex: number;
  onSelect: (index: number) => void;
}

export default function ConceptDots({ concepts, currentIndex, onSelect }: ConceptDotsProps) {
  const completed = concepts.slice(0, currentIndex);
  const remaining = concepts.slice(currentIndex + 1);

  return (
    <div className="flex flex-col gap-3 w-full">
      {/* Dot track */}
      <div className="flex items-center gap-2 flex-wrap justify-center">
        {concepts.map((concept, i) => {
          const isActive  = i === currentIndex;
          const isDone    = i < currentIndex;
          const isPending = i > currentIndex;

          return (
            <button
              key={i}
              onClick={() => onSelect(i)}
              title={concept}
              aria-label={`Concept ${i + 1}: ${concept}`}
              className="relative group flex items-center focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 rounded-full"
            >
              {/* The dot / pill */}
              <motion.div
                animate={{
                  width: isActive ? 36 : 12,
                  height: 12,
                  background: isActive
                    ? '#7c3aed'
                    : isDone
                    ? '#a855f7'
                    : 'rgba(124,58,237,0.18)',
                  boxShadow: isActive
                    ? '0 0 12px rgba(124,58,237,0.6), 0 0 24px rgba(124,58,237,0.2)'
                    : isDone
                    ? '0 0 6px rgba(168,85,247,0.35)'
                    : 'none',
                }}
                transition={{ duration: 0.28, ease: [0.4, 0, 0.2, 1] }}
                className="rounded-full cursor-pointer"
                style={{ minWidth: 12 }}
              />

              {/* Done checkmark overlay */}
              {isDone && (
                <motion.div
                  initial={{ opacity: 0, scale: 0 }}
                  animate={{ opacity: 1, scale: 1 }}
                  style={{
                    position: 'absolute',
                    inset: 0,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <span style={{ fontSize: 7, color: '#fff', fontWeight: 900, lineHeight: 1 }}>✓</span>
                </motion.div>
              )}

              {/* Tooltip */}
              <div
                className="absolute bottom-full left-1/2 -translate-x-1/2 mb-3 px-3 py-2 rounded-xl text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 transition-all duration-200 pointer-events-none z-10 font-semibold"
                style={{
                  background: 'var(--surface)',
                  border: '1px solid rgba(124,58,237,0.25)',
                  color: 'var(--text-1)',
                  boxShadow: '0 6px 20px rgba(124,58,237,0.18)',
                  maxWidth: 240,
                  textAlign: 'center',
                  lineHeight: 1.4,
                  transform: 'translateX(-50%) translateY(-2px)',
                }}
              >
                <span style={{
                  fontSize: 9,
                  fontWeight: 700,
                  color: isActive ? '#7c3aed' : isDone ? '#a855f7' : 'var(--text-4)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.1em',
                  display: 'block',
                  marginBottom: 1,
                }}>
                  {isDone ? 'Done' : isActive ? 'Current' : `Up next`}
                </span>
                {concept}
                {/* Arrow */}
                <div style={{
                  position: 'absolute',
                  bottom: -5,
                  left: '50%',
                  transform: 'translateX(-50%)',
                  width: 0, height: 0,
                  borderLeft: '5px solid transparent',
                  borderRight: '5px solid transparent',
                  borderTop: '5px solid rgba(124,58,237,0.25)',
                }} />
              </div>
            </button>
          );
        })}
      </div>

      {/* Progress info row */}
      <div className="flex items-center justify-center gap-3">
        {/* Progress fraction */}
        <span className="text-xs font-bold tabular-nums" style={{ color: '#7c3aed' }}>
          {currentIndex + 1}<span style={{ color: 'rgba(124,58,237,0.4)', fontWeight: 400 }}>/{concepts.length}</span>
        </span>

        {/* Divider */}
        <span style={{ width: 3, height: 3, borderRadius: '50%', background: 'var(--border-strong)', display: 'inline-block' }} />

        {/* Current concept name */}
        <span className="text-sm font-semibold" style={{ color: 'var(--text-1)' }}>
          {concepts[currentIndex]}
        </span>

        {/* Completed count */}
        {currentIndex > 0 && (
          <>
            <span style={{ width: 3, height: 3, borderRadius: '50%', background: 'var(--border-strong)', display: 'inline-block' }} />
            <span className="text-xs font-medium" style={{ color: '#a855f7' }}>
              {currentIndex} done
            </span>
          </>
        )}
      </div>
    </div>
  );
}
