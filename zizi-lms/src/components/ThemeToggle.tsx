'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

type Theme = 'chalk' | 'cosmic' | 'ocean' | 'forest' | 'sunset' | 'slate' | 'rose';

const THEMES: { id: Theme; label: string; bg: string; dot: string; icon: string }[] = [
  { id: 'chalk',  label: 'Chalk',  bg: '#f8fafc', dot: '#7c3aed', icon: '☀️' },
  { id: 'cosmic', label: 'Cosmic', bg: '#0a0a14', dot: '#8b5cf6', icon: '🌌' },
  { id: 'ocean',  label: 'Ocean',  bg: '#020b18', dot: '#06b6d4', icon: '🌊' },
  { id: 'forest', label: 'Forest', bg: '#020f09', dot: '#10b981', icon: '🌿' },
  { id: 'sunset', label: 'Sunset', bg: '#0f0a06', dot: '#f59e0b', icon: '🌅' },
  { id: 'slate',  label: 'Slate',  bg: '#080c12', dot: '#60a5fa', icon: '🪨' },
  { id: 'rose',   label: 'Rose',   bg: '#fff5f7', dot: '#e11d48', icon: '🌸' },
];

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>('chalk');

  useEffect(() => {
    const saved = localStorage.getItem('zizi-theme') as Theme | null;
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const initial: Theme = saved ?? (prefersDark ? 'cosmic' : 'chalk');
    setThemeState(initial);
    document.documentElement.setAttribute('data-theme', initial);
  }, []);

  const setTheme = (t: Theme) => {
    setThemeState(t);
    document.documentElement.setAttribute('data-theme', t);
    localStorage.setItem('zizi-theme', t);
  };

  return { theme, setTheme };
}

export default function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [open, setOpen] = useState(false);
  const current = THEMES.find(t => t.id === theme) ?? THEMES[0];

  return (
    <div className="relative">
      <motion.button
        onClick={() => setOpen(v => !v)}
        whileHover={{ scale: 1.04 }}
        whileTap={{ scale: 0.95 }}
        title="Choose theme"
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold"
        style={{
          background: 'var(--accent-soft)',
          border: '1px solid var(--border)',
          color: 'var(--text-4)',
          minWidth: 72,
          justifyContent: 'center',
        }}
      >
        {/* Live swatch */}
        <span
          className="w-3 h-3 rounded-full flex-shrink-0"
          style={{ background: current.dot, boxShadow: `0 0 6px ${current.dot}88` }}
        />
        {current.label}
        <motion.span
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          style={{ fontSize: 9, opacity: 0.6 }}
        >▼</motion.span>
      </motion.button>

      {open && (
        <>
          {/* Backdrop */}
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />

          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 top-9 z-50 rounded-2xl overflow-hidden"
            style={{
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              boxShadow: 'var(--shadow-lg)',
              minWidth: 160,
            }}
          >
            <div className="px-3 py-2 border-b" style={{ borderColor: 'var(--border)' }}>
              <p className="text-xs font-bold uppercase tracking-widest" style={{ color: 'var(--text-4)', letterSpacing: '0.15em' }}>
                Theme
              </p>
            </div>
            {THEMES.map(t => (
              <button
                key={t.id}
                onClick={() => { setTheme(t.id); setOpen(false); }}
                className="w-full flex items-center gap-3 px-4 py-2.5 text-left text-sm font-medium transition-colors"
                style={{
                  background: theme === t.id ? 'var(--accent-soft)' : 'transparent',
                  color: theme === t.id ? 'var(--accent)' : 'var(--text-2)',
                }}
              >
                {/* Mini preview swatch */}
                <span
                  className="w-6 h-6 rounded-lg flex-shrink-0 flex items-center justify-center"
                  style={{
                    background: t.bg,
                    border: `2px solid ${t.dot}`,
                    boxShadow: theme === t.id ? `0 0 8px ${t.dot}66` : 'none',
                  }}
                >
                  <span style={{ fontSize: 10 }}>{t.icon}</span>
                </span>
                {t.label}
                {theme === t.id && (
                  <span className="ml-auto text-xs" style={{ color: 'var(--accent)' }}>✓</span>
                )}
              </button>
            ))}
          </motion.div>
        </>
      )}
    </div>
  );
}
