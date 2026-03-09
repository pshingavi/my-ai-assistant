'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion } from 'framer-motion';

const NAV_LINKS = [
  { href: '/', label: 'Galaxy', icon: '🌌' },
  { href: '/learn', label: 'Learn', icon: '📚' },
  { href: '/chat', label: 'Chat', icon: '⚡' },
];

export default function GlobalNav() {
  const pathname = usePathname();

  // Hide nav on /learn/* and /chat — those pages have their own nav
  const hideOn = pathname.startsWith('/learn/') || pathname.startsWith('/chat');
  if (hideOn) return null;

  return (
    <nav
      className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-5 py-3"
      style={{
        borderBottom: '1px solid rgba(139,92,246,0.12)',
        backdropFilter: 'blur(14px)',
        background: 'rgba(10,10,15,0.85)',
      }}
    >
      {/* Logo */}
      <Link href="/" className="flex items-center gap-2 group">
        <motion.span
          animate={{ rotate: [0, 10, -10, 0] }}
          transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
          className="text-xl"
        >
          ⚡
        </motion.span>
        <span className="font-extrabold text-sm hidden sm:block" style={{ color: '#8b5cf6' }}>
          Zizi Byte
        </span>
        <span className="text-xs hidden sm:block" style={{ color: '#334155' }}>
          · Learn in bytes. Think in leaps.
        </span>
      </Link>

      {/* Links */}
      <div className="flex items-center gap-1">
        {NAV_LINKS.map((n) => {
          const active = pathname === n.href || (n.href !== '/' && pathname.startsWith(n.href));
          return (
            <Link
              key={n.href}
              href={n.href}
              className="relative px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 flex items-center gap-1.5"
              style={
                active
                  ? {
                      background: 'rgba(139,92,246,0.2)',
                      color: '#c4b5fd',
                      border: '1px solid rgba(139,92,246,0.35)',
                    }
                  : { color: '#64748b', border: '1px solid transparent' }
              }
            >
              <span>{n.icon}</span>
              {n.label}
              {active && (
                <motion.div
                  layoutId="nav-pill"
                  className="absolute inset-0 rounded-lg"
                  style={{ boxShadow: '0 0 12px rgba(139,92,246,0.3)' }}
                  transition={{ type: 'spring', bounce: 0.2, duration: 0.4 }}
                />
              )}
            </Link>
          );
        })}
      </div>

      {/* Status dot */}
      <div className="flex items-center gap-1.5 text-xs" style={{ color: '#475569' }}>
        <motion.span
          animate={{ opacity: [0.4, 1, 0.4] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="w-1.5 h-1.5 rounded-full inline-block"
          style={{ background: '#22d3ee' }}
        />
        <span className="hidden sm:inline">KG+Dense · Cohere</span>
      </div>
    </nav>
  );
}
