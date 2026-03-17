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

// ── Sparkle ────────────────────────────────────────────────────────────────

function Sparkle({ x, y }: { x: number; y: number }) {
  return (
    <div style={{ position: 'absolute', left: x - 10, top: y - 10, pointerEvents: 'none', zIndex: 20 }}>
      {[...Array(6)].map((_, i) => (
        <motion.div key={i}
          initial={{ x: 0, y: 0, opacity: 1, scale: 1 }}
          animate={{ x: Math.cos((i / 6) * Math.PI * 2) * 18, y: Math.sin((i / 6) * Math.PI * 2) * 18, opacity: 0, scale: 0 }}
          transition={{ duration: 0.8, ease: 'easeOut', delay: i * 0.05 }}
          style={{ position: 'absolute', width: 4, height: 4, borderRadius: '50%', background: '#7c3aed' }}
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
  const [tooltip, setTooltip] = useState<string | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const [sparkles, setSparkles] = useState<{ id: number; x: number; y: number }[]>([]);
  const sparkleId = useRef(0);

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
    <div style={{ position: 'relative', width: '100%', minHeight: '100vh', background: 'var(--bg-1)' }}>
      {/* Subtle dot grid background */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          zIndex: 0,
          backgroundImage: 'radial-gradient(circle, rgba(124,58,237,0.08) 1px, transparent 1px)',
          backgroundSize: '28px 28px',
        }}
      />

      {/* Sparkles (fixed to viewport) */}
      {sparkles.map(s => (
        <div key={s.id} style={{ position: 'fixed', left: s.x, top: s.y, zIndex: 100, pointerEvents: 'none' }}>
          <Sparkle x={0} y={0} />
        </div>
      ))}

      {/* Stats bar */}
      <div style={{
        position: 'relative',
        zIndex: 10,
        display: 'flex',
        alignItems: 'center',
        gap: 20,
        padding: '14px 28px',
        background: 'var(--surface-2)',
        backdropFilter: 'blur(14px)',
        borderBottom: '1px solid var(--border)',
      }}>
        {/* XP */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 16 }}>⚡</span>
          <span style={{ fontWeight: 700, color: 'var(--accent)', fontSize: 14 }}>{xp} XP</span>
        </div>

        {/* Progress */}
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 12, color: 'var(--text-4)', whiteSpace: 'nowrap' }}>
            {visitedCount} of {sorted.length} modules complete
          </span>
          <div style={{ flex: 1, height: 6, borderRadius: 3, background: 'var(--border)', overflow: 'hidden' }}>
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
            style={{
              fontSize: 12, fontWeight: 700, color: '#92400e',
              background: 'rgba(251,191,36,0.15)',
              border: '1px solid rgba(251,191,36,0.4)',
              borderRadius: 20, padding: '4px 10px',
            }}
          >
            🏆 Course Master
          </motion.div>
        )}

        {/* Reset */}
        <button
          onClick={onReset}
          style={{
            fontSize: 11, color: 'var(--text-4)',
            background: 'transparent',
            border: '1px solid var(--border)',
            borderRadius: 8, padding: '4px 10px',
            cursor: 'pointer', transition: 'all 0.2s',
          }}
          onMouseEnter={e => {
            (e.currentTarget as HTMLElement).style.color = '#dc2626';
            (e.currentTarget as HTMLElement).style.borderColor = 'rgba(220,38,38,0.3)';
          }}
          onMouseLeave={e => {
            (e.currentTarget as HTMLElement).style.color = 'var(--text-4)';
            (e.currentTarget as HTMLElement).style.borderColor = 'var(--border)';
          }}
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
                  <path d={d} fill="none" stroke="rgba(124,58,237,0.12)" strokeWidth={2} />
                  <path
                    d={d}
                    fill="none"
                    stroke={visited ? '#7c3aed' : 'rgba(124,58,237,0.3)'}
                    strokeWidth={visited ? 2.5 : 1.5}
                    strokeDasharray="8 12"
                    strokeDashoffset={dashOffset}
                    strokeLinecap="round"
                    opacity={visited ? 0.8 : 0.4}
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
                        ? 'linear-gradient(135deg, rgba(124,58,237,0.1) 0%, rgba(168,85,247,0.08) 100%)'
                        : 'var(--bg-2)',
                      border: visited
                        ? '1.5px solid rgba(124,58,237,0.4)'
                        : '1.5px dashed rgba(124,58,237,0.2)',
                      boxShadow: visited
                        ? '0 4px 20px rgba(124,58,237,0.15), 0 0 0 3px rgba(124,58,237,0.06)'
                        : '0 2px 8px rgba(0,0,0,0.06)',
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
                      color: visited ? '#7c3aed' : 'rgba(124,58,237,0.45)',
                      background: visited ? 'rgba(124,58,237,0.1)' : 'rgba(124,58,237,0.06)',
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
                        fontSize: 10,
                        width: 18,
                        height: 18,
                        borderRadius: '50%',
                        background: 'linear-gradient(135deg, #10b981, #059669)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#fff',
                        boxShadow: '0 2px 8px rgba(16,185,129,0.3)',
                      }}>
                        ✓
                      </div>
                    )}

                    {/* Emoji */}
                    <div style={{ fontSize: 28, lineHeight: 1, opacity: visited ? 1 : 0.55 }}>
                      {emoji}
                    </div>

                    {/* Name */}
                    <div style={{
                      fontSize: 10.5,
                      fontWeight: 600,
                      color: visited ? 'var(--text-1)' : 'var(--text-3)',
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

                    {/* Pulse ring for visited */}
                    {visited && (
                      <motion.div
                        animate={{ opacity: [0.3, 0.6, 0.3] }}
                        transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
                        style={{
                          position: 'absolute',
                          inset: -4,
                          borderRadius: 20,
                          border: '1px solid rgba(124,58,237,0.25)',
                          pointerEvents: 'none',
                        }}
                      />
                    )}
                  </motion.div>
                </Link>
              </motion.div>
            );
          })}

          {/* Spacer */}
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
          background: 'var(--bg-2)',
          border: '1px solid var(--border)',
          borderRadius: 8,
          padding: '5px 10px',
          fontSize: 11,
          color: 'var(--text-1)',
          fontWeight: 600,
          whiteSpace: 'nowrap',
          zIndex: 9999,
          pointerEvents: 'none',
          backdropFilter: 'blur(8px)',
          boxShadow: '0 4px 16px rgba(0,0,0,0.1)',
        }}>
          {tooltip}
        </div>
      )}
    </div>
  );
}
