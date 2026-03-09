'use client';

import { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface Props {
  onSend: (msg: string) => void;
  disabled?: boolean;
}

const SUGGESTIONS = [
  'Explain the agent loop like I\'m 5',
  'What is RAG and why does it matter?',
  'How does LangGraph handle state?',
  'Explain embeddings to someone who cooks',
  'What are RAGAS evaluation metrics?',
];

export default function ChatInput({ onSend, disabled }: Props) {
  const [value, setValue] = useState('');
  const [focused, setFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 160) + 'px';
  }, [value]);

  const handleSend = () => {
    const msg = value.trim();
    if (!msg || disabled) return;
    onSend(msg);
    setValue('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="space-y-2">
      {/* Suggestion chips — only when empty + not disabled */}
      <AnimatePresence>
        {!value && !disabled && (
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            className="flex flex-wrap gap-1.5 px-1"
          >
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => { setValue(s); textareaRef.current?.focus(); }}
                className="px-3 py-1 rounded-full text-xs transition-all duration-200"
                style={{
                  background: 'rgba(139,92,246,0.08)',
                  border: '1px solid rgba(139,92,246,0.2)',
                  color: '#94a3b8',
                }}
                onMouseEnter={(e) => {
                  (e.target as HTMLButtonElement).style.borderColor = 'rgba(139,92,246,0.5)';
                  (e.target as HTMLButtonElement).style.color = '#c4b5fd';
                }}
                onMouseLeave={(e) => {
                  (e.target as HTMLButtonElement).style.borderColor = 'rgba(139,92,246,0.2)';
                  (e.target as HTMLButtonElement).style.color = '#94a3b8';
                }}
              >
                {s}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input row */}
      <div
        className="relative flex items-end gap-2 rounded-2xl p-2 transition-all duration-300"
        style={{
          background: 'rgba(255,255,255,0.04)',
          border: focused
            ? '1px solid rgba(139,92,246,0.6)'
            : '1px solid rgba(255,255,255,0.08)',
          boxShadow: focused ? '0 0 20px rgba(139,92,246,0.15)' : 'none',
        }}
      >
        {/* Glow ring when focused */}
        {focused && (
          <motion.div
            className="absolute inset-0 rounded-2xl pointer-events-none"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            style={{ boxShadow: '0 0 0 1px rgba(139,92,246,0.3) inset' }}
          />
        )}

        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKey}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder="Ask anything about AI engineering…"
          disabled={disabled}
          rows={1}
          className="flex-1 bg-transparent resize-none outline-none text-sm leading-relaxed py-2 px-2"
          style={{
            color: '#f1f5f9',
            caretColor: '#8b5cf6',
            maxHeight: 160,
            fontFamily: 'Inter, sans-serif',
          }}
        />

        {/* Send button */}
        <motion.button
          onClick={handleSend}
          disabled={!value.trim() || disabled}
          whileTap={{ scale: 0.9 }}
          className="flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center transition-all duration-200"
          style={{
            background: value.trim() && !disabled
              ? 'linear-gradient(135deg, #8b5cf6, #22d3ee)'
              : 'rgba(255,255,255,0.06)',
            cursor: value.trim() && !disabled ? 'pointer' : 'not-allowed',
            boxShadow: value.trim() && !disabled ? '0 0 12px rgba(139,92,246,0.5)' : 'none',
          }}
        >
          {disabled ? (
            <motion.span
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
              className="block w-4 h-4 rounded-full border-2 border-t-transparent"
              style={{ borderColor: '#8b5cf6', borderTopColor: 'transparent' }}
            />
          ) : (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M22 2L11 13" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M22 2L15 22L11 13L2 9L22 2Z" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          )}
        </motion.button>
      </div>

      <p className="text-xs text-center" style={{ color: '#334155' }}>
        Shift+Enter for new line · powered by KG+Dense → Cohere Rerank
      </p>
    </div>
  );
}
