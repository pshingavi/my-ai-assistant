'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import dynamic from 'next/dynamic';

const ArchitectureFlow = dynamic(
  () => import('@/src/components/ArchitectureFlow'),
  { ssr: false, loading: () => (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#7c3aed', fontSize: 14 }}>
      Loading diagram…
    </div>
  ) }
);

const TABS = [
  { id: 'system',  label: 'Full System',      icon: '🏗️', desc: 'All services and how they connect' },
  { id: 'lms',     label: 'LMS Pipeline',     icon: '📚', desc: 'Byte generation, caching, rendering' },
  { id: 'chat',    label: 'Chat Pipeline',    icon: '⚡', desc: 'KG+Dense → Cohere → GPT-4o stream' },
  { id: 'content', label: 'Content Pipeline', icon: '🔄', desc: 'Research → dedup → post → ingest' },
];

export default function ArchitecturePage() {
  const [activeTab, setActiveTab] = useState('system');

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg-1)', paddingTop: 57 }}>
      {/* Header */}
      <div
        style={{
          padding: '16px 28px 0',
          borderBottom: '1px solid var(--border)',
          background: 'var(--surface-2)',
          backdropFilter: 'blur(12px)',
          flexShrink: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
          <span style={{ fontSize: 20 }}>🏛️</span>
          <div>
            <h1 style={{ fontWeight: 800, fontSize: 18, color: 'var(--text-1)', margin: 0 }}>
              Architecture
            </h1>
            <p style={{ fontSize: 11, color: 'var(--text-4)', margin: 0 }}>
              Click any node to dive deep — what it does, why it&apos;s there, how it&apos;s used
            </p>
          </div>
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 4 }}>
          {TABS.map((tab) => {
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  position: 'relative',
                  padding: '8px 16px',
                  borderRadius: '10px 10px 0 0',
                  border: 'none',
                  cursor: 'pointer',
                  background: active ? 'var(--bg-1)' : 'transparent',
                  color: active ? 'var(--accent)' : 'var(--text-3)',
                  fontWeight: active ? 700 : 500,
                  fontSize: 12.5,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  transition: 'all 0.15s',
                  borderBottom: active ? '2px solid var(--accent)' : '2px solid transparent',
                  whiteSpace: 'nowrap',
                }}
              >
                <span>{tab.icon}</span>
                {tab.label}
                {active && (
                  <motion.div
                    layoutId="tab-indicator"
                    style={{
                      position: 'absolute', bottom: -2, left: 0, right: 0,
                      height: 2, background: 'var(--accent)', borderRadius: 1,
                    }}
                  />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Active tab description */}
      <div
        style={{
          padding: '6px 28px',
          background: 'rgba(124,58,237,0.04)',
          borderBottom: '1px solid var(--border)',
          flexShrink: 0,
        }}
      >
        <p style={{ fontSize: 11, color: 'var(--text-4)', margin: 0 }}>
          {TABS.find(t => t.id === activeTab)?.desc}
        </p>
      </div>

      {/* Diagram — key forces remount + fitView on tab switch */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <ArchitectureFlow key={activeTab} diagramId={activeTab} />
      </div>
    </div>
  );
}
