'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion } from 'framer-motion';
import ThemeToggle from './ThemeToggle';

const NAV_LINKS = [
  { href: '/', label: 'Galaxy', icon: '🌌' },
  { href: '/learn', label: 'Learn', icon: '📚' },
  { href: '/chat', label: 'Chat', icon: '⚡' },
  { href: '/architecture', label: 'Architecture', icon: '🏛️' },
  { href: '/qa', label: 'Q&A', icon: '❓' },
];

export default function GlobalNav() {
  const pathname = usePathname();

  // Hide nav on /learn/* and /chat — those pages have their own nav
  const hideOn = pathname.startsWith('/learn/') || pathname.startsWith('/chat');
  if (hideOn) return null;

  return (
    <nav
      className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 py-3.5"
      style={{
        borderBottom: '1px solid var(--border)',
        backdropFilter: 'blur(16px)',
        background: 'var(--surface-2)',
        boxShadow: '0 1px 0 var(--border)',
      }}
    >
      {/* Logo */}
      <Link href="/" className="flex items-center gap-2.5 group">
        <motion.span
          animate={{ rotate: [0, 10, -10, 0] }}
          transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
          className="text-xl"
        >
          ⚡
        </motion.span>
        <span className="font-extrabold text-sm hidden sm:block" style={{ color: 'var(--accent)' }}>
          Zizi Byte
        </span>
        <span className="text-xs hidden lg:block" style={{ color: 'var(--text-4)', fontStyle: 'italic' }}>
          · Learn in bytes. Think in leaps.
        </span>
      </Link>

      {/* Links */}
      <div className="flex items-center gap-1 p-1 rounded-xl" style={{ background: 'var(--bg-2)', border: '1px solid var(--border)' }}>
        {NAV_LINKS.map((n) => {
          const active = pathname === n.href || (n.href !== '/' && pathname.startsWith(n.href));
          return (
            <Link
              key={n.href}
              href={n.href}
              className="relative px-4 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 flex items-center gap-1.5"
              style={
                active
                  ? { background: 'var(--accent)', color: '#fff', boxShadow: '0 2px 8px rgba(124,58,237,0.35)' }
                  : { color: 'var(--text-3)' }
              }
              onMouseEnter={e => {
                if (!active) (e.currentTarget as HTMLElement).style.color = 'var(--text-1)';
              }}
              onMouseLeave={e => {
                if (!active) (e.currentTarget as HTMLElement).style.color = 'var(--text-3)';
              }}
            >
              <span>{n.icon}</span>
              {n.label}
            </Link>
          );
        })}
      </div>

      {/* Right: status + theme */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 text-xs hidden sm:flex px-3 py-1.5 rounded-lg" style={{ color: 'var(--text-4)', background: 'var(--bg-2)', border: '1px solid var(--border)' }}>
          <motion.span
            animate={{ opacity: [0.4, 1, 0.4] }}
            transition={{ duration: 2, repeat: Infinity }}
            className="w-1.5 h-1.5 rounded-full inline-block"
            style={{ background: 'var(--accent)' }}
          />
          KG+Dense · Cohere
        </div>
        <ThemeToggle />
      </div>
    </nav>
  );
}
