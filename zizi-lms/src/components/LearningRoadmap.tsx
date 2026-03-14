'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import type { TopicSummary } from '@/src/types';

const MODULE_EMOJIS: Record<string, string> = {
  '01': '🧠', '02': '🔍', '03': '🤖', '04': '📚', '05': '🕸️',
  '06': '💾', '07': '🚀', '08': '🔬', '09': '🧪', '10': '📊',
  '11': '⚡', '14': '🔌', '15': '🛰️', '16': '🖥️', '17': '🤝', '18': '🛡️',
};

const COLS = 4;
const NODE_W = 148;
const NODE_H = 100;
const GAP_X = 90;
const GAP_Y = 80;
const PAD_X = 70;
const PAD_Y = 60;

interface NodePos { x: number; y: number; topic: TopicSummary }

function getPositions(topics: TopicSummary[]): NodePos[] {
  return topics.map((topic, i) => {
    const row = Math.floor(i / COLS);
    const col = row % 2 === 0 ? i % COLS : COLS - 1 - (i % COLS);
    const x = PAD_X + col * (NODE_W + GAP_X);
    const y = PAD_Y + row * (NODE_H + GAP_Y);
    return { x, y, topic };
  });
}

function svgPathBetween(a: NodePos, b: NodePos): string {
  const ax = a.x + NODE_W / 2;
  const ay = a.y + NODE_H / 2;
  const bx = b.x + NODE_W / 2;
  const by = b.y + NODE_H / 2;
  const cx = (ax + bx) / 2;
  const cy = (ay + by) / 2;
  return `M ${ax} ${ay} Q ${cx} ${ay} ${bx} ${by}`;
}

// ── Background themes ──────────────────────────────────────────────────────

const CosmicBg = () => (
  <div className="fixed inset-0 pointer-events-none" style={{ zIndex: 0, overflow: 'hidden', background: 'radial-gradient(ellipse 120% 80% at 50% 10%, #0d0520 0%, #050210 60%, #000 100%)' }}>
    <style>{`
      @keyframes twinkle { 0%,100%{opacity:0.15} 50%{opacity:0.9} }
      @keyframes nebula-drift { 0%{transform:translateX(0) translateY(0) scale(1)} 50%{transform:translateX(30px) translateY(-20px) scale(1.05)} 100%{transform:translateX(0) translateY(0) scale(1)} }
    `}</style>
    {Array.from({ length: 60 }).map((_, i) => (
      <div key={i} style={{
        position: 'absolute',
        left: `${(i * 37 + 13) % 100}%`,
        top: `${(i * 53 + 7) % 100}%`,
        width: i % 5 === 0 ? 3 : i % 3 === 0 ? 2 : 1,
        height: i % 5 === 0 ? 3 : i % 3 === 0 ? 2 : 1,
        borderRadius: '50%',
        background: '#fff',
        animation: `twinkle ${2 + (i % 4)}s ${(i * 0.3) % 3}s ease-in-out infinite`,
      }} />
    ))}
    <div style={{ position: 'absolute', top: '10%', left: '20%', width: 500, height: 300, background: 'radial-gradient(ellipse, rgba(124,58,237,0.12) 0%, transparent 70%)', filter: 'blur(40px)', animation: 'nebula-drift 18s ease-in-out infinite' }} />
    <div style={{ position: 'absolute', bottom: '20%', right: '10%', width: 400, height: 250, background: 'radial-gradient(ellipse, rgba(6,182,212,0.08) 0%, transparent 70%)', filter: 'blur(40px)', animation: 'nebula-drift 22s 4s ease-in-out infinite' }} />
  </div>
);

const CircuitBg = () => (
  <div className="fixed inset-0 pointer-events-none" style={{ zIndex: 0, background: '#050f05' }}>
    <style>{`
      @keyframes pulse-line { 0%,100%{opacity:0.04} 50%{opacity:0.18} }
    `}</style>
    <svg width="100%" height="100%" style={{ position: 'absolute', inset: 0 }}>
      <defs>
        <pattern id="circuit" x="0" y="0" width="80" height="80" patternUnits="userSpaceOnUse">
          <path d="M0 40 H30 M50 40 H80 M40 0 V30 M40 50 V80" stroke="#00ff41" strokeWidth="0.4" fill="none" opacity="0.12" />
          <circle cx="40" cy="40" r="3" fill="none" stroke="#00ff41" strokeWidth="0.5" opacity="0.15" />
          <circle cx="30" cy="40" r="1.5" fill="#00ff41" opacity="0.1" />
          <circle cx="50" cy="40" r="1.5" fill="#00ff41" opacity="0.1" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#circuit)" />
    </svg>
    {Array.from({ length: 8 }).map((_, i) => (
      <div key={i} style={{
        position: 'absolute',
        left: `${(i * 12 + 5) % 90}%`,
        top: `${(i * 17 + 3) % 90}%`,
        width: 2, height: `${60 + i * 20}px`,
        background: 'linear-gradient(to bottom, transparent, #00ff41, transparent)',
        opacity: 0.12,
        animation: `pulse-line ${3 + i}s ${i * 0.5}s ease-in-out infinite`,
      }} />
    ))}
  </div>
);

const WaveBg = () => (
  <div className="fixed inset-0 pointer-events-none" style={{ zIndex: 0, background: '#020818', overflow: 'hidden' }}>
    <style>{`
      @keyframes wave-move { 0%{transform:translateX(0)} 100%{transform:translateX(-50%)} }
    `}</style>
    {[0, 1, 2].map(i => (
      <div key={i} style={{
        position: 'absolute',
        bottom: `${i * 15}%`,
        left: 0,
        width: '200%',
        height: `${100 + i * 40}px`,
        opacity: 0.06 - i * 0.015,
        background: `radial-gradient(ellipse 50% 100% at 25% 50%, #1e40af, transparent),radial-gradient(ellipse 50% 100% at 75% 50%, #0e7490, transparent)`,
        borderRadius: '50% 50% 0 0',
        animation: `wave-move ${12 + i * 4}s linear infinite`,
        animationDelay: `${i * -3}s`,
      }} />
    ))}
  </div>
);

const MatrixBg = () => (
  <div className="fixed inset-0 pointer-events-none" style={{ zIndex: 0, background: '#010a01', overflow: 'hidden' }}>
    <style>{`
      @keyframes fall { 0%{transform:translateY(-100%);opacity:0} 10%{opacity:1} 90%{opacity:1} 100%{transform:translateY(100vh);opacity:0} }
    `}</style>
    {Array.from({ length: 20 }).map((_, i) => (
      <div key={i} style={{
        position: 'absolute',
        left: `${i * 5 + 1}%`,
        top: 0,
        color: '#00ff41',
        fontSize: 10,
        fontFamily: 'monospace',
        opacity: 0.07,
        animation: `fall ${6 + (i % 5) * 2}s ${(i * 0.8) % 5}s linear infinite`,
        userSelect: 'none',
        whiteSpace: 'nowrap',
        letterSpacing: 4,
        writingMode: 'vertical-rl',
      }}>
        {'01アイAI10ニュー01アイ10'.split('').map((c, j) => (
          <span key={j} style={{ opacity: Math.random() > 0.5 ? 1 : 0.3 }}>{c}</span>
        ))}
      </div>
    ))}
  </div>
);

const AuroraBg = () => (
  <div className="fixed inset-0 pointer-events-none" style={{ zIndex: 0, background: '#030a0f', overflow: 'hidden' }}>
    <style>{`
      @keyframes aurora1 { 0%,100%{transform:rotate(-5deg) scaleY(1)} 50%{transform:rotate(5deg) scaleY(1.3)} }
      @keyframes aurora2 { 0%,100%{transform:rotate(3deg) scaleY(1.1)} 50%{transform:rotate(-4deg) scaleY(0.9)} }
    `}</style>
    <div style={{ position: 'absolute', top: '-20%', left: '-10%', width: '70%', height: '60%', background: 'linear-gradient(160deg, rgba(124,58,237,0.15) 0%, rgba(6,182,212,0.1) 50%, transparent 100%)', filter: 'blur(60px)', transformOrigin: 'center bottom', animation: 'aurora1 14s ease-in-out infinite' }} />
    <div style={{ position: 'absolute', top: '-10%', right: '-10%', width: '60%', height: '50%', background: 'linear-gradient(200deg, rgba(16,185,129,0.1) 0%, rgba(124,58,237,0.08) 50%, transparent 100%)', filter: 'blur(50px)', transformOrigin: 'center bottom', animation: 'aurora2 18s ease-in-out infinite' }} />
    <div style={{ position: 'absolute', bottom: '10%', left: '20%', width: '60%', height: '30%', background: 'radial-gradient(ellipse, rgba(6,182,212,0.06) 0%, transparent 70%)', filter: 'blur(40px)' }} />
  </div>
);

const BG_COMPONENTS = [CosmicBg, CircuitBg, WaveBg, MatrixBg, AuroraBg];

// ── Sparkle ────────────────────────────────────────────────────────────────

function Sparkle({ x, y }: { x: number; y: number }) {
  return (
    <div style={{ position: 'absolute', left: x - 10, top: y - 10, pointerEvents: 'none', zIndex: 20 }}>
      {[...Array(6)].map((_, i) => (
        <motion.div key={i}
          initial={{ x: 0, y: 0, opacity: 1, scale: 1 }}
          animate={{ x: Math.cos((i / 6) * Math.PI * 2) * 18, y: Math.sin((i / 6) * Math.PI * 2) * 18, opacity: 0, scale: 0 }}
          transition={{ duration: 0.8, ease: 'easeOut', delay: i * 0.05 }}
          style={{ position: 'absolute', width: 4, height: 4, borderRadius: '50%', background: '#a855f7' }}
        />
      ))}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────

interface Props {
  topics: TopicSummary[];
  visitedTopicIds: Set<string>;
  onReset: () => void;
}

export default function LearningRoadmap({ topics, visitedTopicIds, onReset }: Props) {
  const [BgComponent] = useState(() => BG_COMPONENTS[Math.floor(Math.random() * BG_COMPONENTS.length)]);
  const [tooltip, setTooltip] = useState<string | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const [sparkles, setSparkles] = useState<{ id: number; x: number; y: number }[]>([]);
  const sparkleId = useRef(0);
  const pathRef = useRef<SVGPathElement | null>(null);

  const sorted = [...topics]
    .filter(t => !t.is_post && !!t.module_number)
    .sort((a, b) => (a.module_number || '').localeCompare(b.module_number || ''));

  const positions = getPositions(sorted);
  const totalW = COLS * (NODE_W + GAP_X) - GAP_X + PAD_X * 2;
  const rows = Math.ceil(sorted.length / COLS);
  const totalH = rows * (NODE_H + GAP_Y) - GAP_Y + PAD_Y * 2;

  const visitedCount = sorted.filter(t => visitedTopicIds.has(t.id)).length;
  const allDone = visitedCount === sorted.length && sorted.length > 0;
  const xp = visitedCount;

  function handleVisitedNodeClick(e: React.MouseEvent, pos: NodePos) {
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const sid = ++sparkleId.current;
    setSparkles(prev => [...prev, { id: sid, x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 }]);
    setTimeout(() => setSparkles(prev => prev.filter(s => s.id !== sid)), 900);
  }

  // Animated dash offset for SVG paths
  const [dashOffset, setDashOffset] = useState(0);
  useEffect(() => {
    let frame: number;
    let val = 0;
    const tick = () => {
      val = (val - 1.5) % 20;
      setDashOffset(val);
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, []);

  return (
    <div style={{ position: 'relative', width: '100%', minHeight: '100vh' }}>
      {/* Background */}
      <BgComponent />

      {/* Sparkles (fixed to viewport) */}
      {sparkles.map(s => (
        <div key={s.id} style={{ position: 'fixed', left: s.x, top: s.y, zIndex: 100, pointerEvents: 'none' }}>
          <Sparkle x={0} y={0} />
        </div>
      ))}

      {/* Stats bar */}
      <div style={{ position: 'relative', zIndex: 10, display: 'flex', alignItems: 'center', gap: 20, padding: '18px 28px', background: 'rgba(10,4,20,0.75)', backdropFilter: 'blur(14px)', borderBottom: '1px solid rgba(124,58,237,0.22)' }}>
        {/* XP */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 18 }}>⚡</span>
          <span style={{ fontWeight: 700, color: '#a855f7', fontSize: 15 }}>{xp} XP</span>
        </div>

        {/* Progress */}
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.55)', whiteSpace: 'nowrap' }}>
            {visitedCount} of {sorted.length} modules complete
          </span>
          <div style={{ flex: 1, height: 6, borderRadius: 3, background: 'rgba(255,255,255,0.1)', overflow: 'hidden' }}>
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${sorted.length ? (visitedCount / sorted.length) * 100 : 0}%` }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
              style={{ height: '100%', borderRadius: 3, background: 'linear-gradient(90deg, #7c3aed, #a855f7)' }}
            />
          </div>
        </div>

        {/* Badge */}
        {allDone && (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', stiffness: 300 }}
            style={{ fontSize: 12, fontWeight: 700, color: '#fbbf24', background: 'rgba(251,191,36,0.1)', border: '1px solid rgba(251,191,36,0.3)', borderRadius: 20, padding: '4px 10px' }}
          >
            🏆 Course Master
          </motion.div>
        )}

        {/* Reset */}
        <button
          onClick={onReset}
          style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', background: 'transparent', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, padding: '4px 10px', cursor: 'pointer', transition: 'all 0.2s' }}
          onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = 'rgba(255,80,80,0.8)'; (e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,80,80,0.3)'; }}
          onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = 'rgba(255,255,255,0.35)'; (e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,0.1)'; }}
        >
          ↺ Reset
        </button>
      </div>

      {/* Roadmap scroll area */}
      <div style={{ position: 'relative', zIndex: 10, overflowX: 'auto', overflowY: 'auto', padding: '20px 0 40px' }}>
        <div style={{ position: 'relative', margin: '0 auto', width: totalW }}>

          {/* SVG paths */}
          <svg
            width={totalW}
            height={totalH}
            style={{ position: 'absolute', inset: 0, pointerEvents: 'none', overflow: 'visible' }}
          >
            {positions.map((pos, i) => {
              if (i === positions.length - 1) return null;
              const next = positions[i + 1];
              const d = svgPathBetween(pos, next);
              const visited = visitedTopicIds.has(pos.topic.id) && visitedTopicIds.has(next.topic.id);
              return (
                <g key={i}>
                  {/* base path */}
                  <path d={d} fill="none" stroke="rgba(124,58,237,0.15)" strokeWidth={2} />
                  {/* animated dash */}
                  <path
                    d={d}
                    fill="none"
                    stroke={visited ? '#a855f7' : 'rgba(124,58,237,0.35)'}
                    strokeWidth={visited ? 2.5 : 1.5}
                    strokeDasharray="8 12"
                    strokeDashoffset={dashOffset}
                    strokeLinecap="round"
                    opacity={visited ? 0.9 : 0.4}
                  />
                </g>
              );
            })}
          </svg>

          {/* Nodes */}
          {positions.map((pos, i) => {
            const topic = pos.topic;
            const visited = visitedTopicIds.has(topic.id);
            const emoji = MODULE_EMOJIS[topic.module_number] ?? '📘';

            return (
              <motion.div
                key={topic.id}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.05, duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
                style={{
                  position: 'absolute',
                  left: pos.x,
                  top: pos.y,
                  width: NODE_W,
                  height: NODE_H,
                }}
                onMouseEnter={(e) => {
                  setTooltip(topic.name);
                  const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
                  setTooltipPos({ x: r.left + r.width / 2, y: r.top - 8 });
                }}
                onMouseLeave={() => setTooltip(null)}
              >
                <Link
                  href={`/learn/${topic.id}`}
                  onClick={visited ? (e) => handleVisitedNodeClick(e, pos) : undefined}
                  style={{ display: 'block', width: '100%', height: '100%', textDecoration: 'none' }}
                >
                  <motion.div
                    whileHover={{ scale: 1.08, zIndex: 20 }}
                    style={{
                      width: '100%',
                      height: '100%',
                      borderRadius: 16,
                      position: 'relative',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: 4,
                      background: visited
                        ? 'linear-gradient(135deg, rgba(124,58,237,0.25) 0%, rgba(168,85,247,0.2) 100%)'
                        : 'rgba(10,4,20,0.7)',
                      border: visited
                        ? '1.5px solid rgba(168,85,247,0.6)'
                        : '1.5px dashed rgba(124,58,237,0.25)',
                      boxShadow: visited
                        ? '0 0 20px rgba(124,58,237,0.35), 0 0 6px rgba(168,85,247,0.2)'
                        : '0 2px 8px rgba(0,0,0,0.4)',
                      backdropFilter: 'blur(8px)',
                      cursor: 'pointer',
                      transition: 'box-shadow 0.2s, border-color 0.2s',
                    }}
                  >
                    {/* Module badge */}
                    <div style={{
                      position: 'absolute',
                      top: 6,
                      left: 8,
                      fontSize: 9,
                      fontWeight: 700,
                      fontFamily: 'monospace',
                      color: visited ? '#c084fc' : 'rgba(124,58,237,0.5)',
                      background: visited ? 'rgba(124,58,237,0.2)' : 'rgba(124,58,237,0.08)',
                      borderRadius: 4,
                      padding: '1px 5px',
                      lineHeight: 1.6,
                    }}>
                      {topic.module_number}
                    </div>

                    {/* Checkmark badge */}
                    {visited && (
                      <div style={{
                        position: 'absolute',
                        top: 4,
                        right: 6,
                        fontSize: 11,
                        width: 18,
                        height: 18,
                        borderRadius: '50%',
                        background: 'linear-gradient(135deg, #10b981, #059669)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        boxShadow: '0 0 8px rgba(16,185,129,0.5)',
                      }}>
                        ✓
                      </div>
                    )}

                    {/* Emoji */}
                    <div style={{ fontSize: 28, lineHeight: 1, filter: visited ? 'none' : 'grayscale(0.4) opacity(0.6)' }}>
                      {emoji}
                    </div>

                    {/* Name */}
                    <div style={{
                      fontSize: 10.5,
                      fontWeight: 600,
                      color: visited ? 'rgba(255,255,255,0.92)' : 'rgba(255,255,255,0.45)',
                      textAlign: 'center',
                      padding: '0 8px',
                      lineHeight: 1.35,
                      maxWidth: '100%',
                      overflow: 'hidden',
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                    } as React.CSSProperties}>
                      {topic.name}
                    </div>

                    {/* Glow ring for visited */}
                    {visited && (
                      <motion.div
                        animate={{ opacity: [0.4, 0.7, 0.4] }}
                        transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
                        style={{
                          position: 'absolute',
                          inset: -4,
                          borderRadius: 20,
                          border: '1px solid rgba(168,85,247,0.3)',
                          pointerEvents: 'none',
                        }}
                      />
                    )}
                  </motion.div>
                </Link>
              </motion.div>
            );
          })}

          {/* Invisible spacer to give the container correct height */}
          <div style={{ height: totalH, width: totalW }} />
        </div>
      </div>

      {/* Tooltip (fixed) */}
      {tooltip && (
        <div style={{
          position: 'fixed',
          left: tooltipPos.x,
          top: tooltipPos.y,
          transform: 'translateX(-50%) translateY(-100%)',
          background: 'rgba(10,4,20,0.95)',
          border: '1px solid rgba(124,58,237,0.4)',
          borderRadius: 8,
          padding: '5px 10px',
          fontSize: 11,
          color: 'rgba(255,255,255,0.9)',
          fontWeight: 600,
          whiteSpace: 'nowrap',
          zIndex: 9999,
          pointerEvents: 'none',
          backdropFilter: 'blur(8px)',
          boxShadow: '0 4px 16px rgba(0,0,0,0.5)',
        }}>
          {tooltip}
        </div>
      )}
    </div>
  );
}
