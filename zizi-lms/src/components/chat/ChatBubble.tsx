'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { useState } from 'react';
import type { ChatMsg } from '@/src/store/chatStore';

function SourcePill({ source, score }: { source: string; score: number }) {
  const name = source.split('/').pop() || source;
  const short = name.length > 32 ? name.slice(0, 29) + '…' : name;
  const color = score > 0.7 ? '#22d3ee' : score > 0.4 ? '#8b5cf6' : '#64748b';
  return (
    <span
      title={`${source} (relevance: ${score.toFixed(2)})`}
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs cursor-default"
      style={{ background: 'rgba(255,255,255,0.06)', border: `1px solid ${color}44`, color }}
    >
      <span style={{ color }}>◆</span> {short} <span style={{ color: '#475569' }}>{score.toFixed(2)}</span>
    </span>
  );
}

function StepBadge({ step, index }: { step: string; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.12 }}
      className="flex items-center gap-2 text-xs py-1"
      style={{ color: '#475569' }}
    >
      <motion.span
        animate={{ opacity: [0.4, 1, 0.4] }}
        transition={{ duration: 1.5, repeat: Infinity }}
        style={{ color: '#8b5cf6' }}
      >●</motion.span>
      {step}
    </motion.div>
  );
}

function ThinkingDots() {
  return (
    <div className="flex items-center gap-1.5 py-1 px-1">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="w-1.5 h-1.5 rounded-full"
          style={{ background: '#8b5cf6' }}
          animate={{ scale: [1, 1.5, 1], opacity: [0.4, 1, 0.4] }}
          transition={{ duration: 1, repeat: Infinity, delay: i * 0.2 }}
        />
      ))}
    </div>
  );
}

// Typewriter cursor
function Cursor() {
  return (
    <motion.span
      animate={{ opacity: [1, 0] }}
      transition={{ duration: 0.6, repeat: Infinity, repeatType: 'reverse' }}
      style={{ display: 'inline-block', width: 2, height: '1em', background: '#8b5cf6',
        marginLeft: 2, verticalAlign: 'text-bottom', borderRadius: 1 }}
    />
  );
}

export default function ChatBubble({ msg }: { msg: ChatMsg }) {
  const isUser = msg.role === 'user';
  const [showSources, setShowSources] = useState(false);
  const isEmpty = !msg.content && msg.streaming;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
      className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'} items-end max-w-full`}
    >
      {/* Avatar */}
      <div
        className="flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center text-sm font-bold"
        style={isUser
          ? { background: 'linear-gradient(135deg,#8b5cf6,#22d3ee)', color: 'white' }
          : { background: 'rgba(139,92,246,0.15)', border: '1px solid rgba(139,92,246,0.35)', color: '#8b5cf6' }
        }
      >
        {isUser ? 'Y' : '⚡'}
      </div>

      <div className={`flex flex-col gap-1.5 max-w-[78%] ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Pipeline steps (assistant only) */}
        {!isUser && msg.steps && msg.steps.length > 0 && (
          <div className="w-full space-y-0.5 mb-1">
            {msg.steps.map((s, i) => <StepBadge key={i} step={s} index={i} />)}
          </div>
        )}

        {/* Bubble */}
        <div
          className="px-4 py-3 rounded-2xl text-sm leading-relaxed relative"
          style={isUser
            ? {
                background: 'linear-gradient(135deg, rgba(139,92,246,0.25), rgba(34,211,238,0.15))',
                border: '1px solid rgba(139,92,246,0.35)',
                color: '#f1f5f9',
                borderBottomRightRadius: 6,
              }
            : {
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.09)',
                color: '#e2e8f0',
                borderBottomLeftRadius: 6,
              }
          }
        >
          {isEmpty ? (
            <ThinkingDots />
          ) : (
            <>
              <span style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</span>
              {msg.streaming && <Cursor />}
            </>
          )}
        </div>

        {/* Sources */}
        {!isUser && msg.sources && msg.sources.length > 0 && !msg.streaming && (
          <div className="w-full">
            <button
              onClick={() => setShowSources((v) => !v)}
              className="flex items-center gap-1.5 text-xs transition-colors mb-1"
              style={{ color: showSources ? '#8b5cf6' : '#475569' }}
            >
              <motion.span
                animate={{ rotate: showSources ? 90 : 0 }}
                transition={{ duration: 0.2 }}
              >▶</motion.span>
              📚 {msg.sources.length} source{msg.sources.length > 1 ? 's' : ''}
            </button>
            <AnimatePresence>
              {showSources && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {msg.sources.map((s, i) => (
                      <SourcePill key={i} source={s.source} score={s.score} />
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}
      </div>
    </motion.div>
  );
}
