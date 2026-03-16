import { Suspense } from 'react';
import { fetchAllQA } from '@/src/lib/api';
import QAExplorer from '@/src/components/QAExplorer';
import type { TopicQA } from '@/src/types';

export const dynamic = 'force-dynamic';

export default async function QAPage() {
  let topics: TopicQA[] = [];
  try {
    topics = await fetchAllQA();
  } catch {
    // API not ready yet — render empty state
  }

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg-1)', paddingTop: 57 }}>
      {/* Header */}
      <div style={{
        padding: '14px 28px',
        borderBottom: '1px solid var(--border)',
        background: 'var(--surface-2)',
        backdropFilter: 'blur(12px)',
        flexShrink: 0,
        display: 'flex', alignItems: 'center', gap: 10,
      }}>
        <span style={{ fontSize: 20 }}>❓</span>
        <div>
          <h1 style={{ fontWeight: 800, fontSize: 17, color: 'var(--text-1)', margin: 0 }}>
            Q&amp;A Explorer
          </h1>
          <p style={{ fontSize: 11, color: 'var(--text-4)', margin: 0 }}>
            RAG-grounded Q&amp;A for every AIE9 topic · click any question to expand · ask your own below
          </p>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, color: 'var(--text-5)' }}>
          {topics.length > 0 ? (
            <>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#10b981', display: 'inline-block' }} />
              {topics.length} topics loaded
            </>
          ) : (
            <>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#f59e0b', display: 'inline-block' }} />
              Run gen_qa.py to populate
            </>
          )}
        </div>
      </div>

      {/* Explorer */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        {topics.length === 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 16 }}>
            <span style={{ fontSize: 48 }}>📭</span>
            <div style={{ textAlign: 'center' }}>
              <p style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-2)', margin: '0 0 8px' }}>No Q&amp;A generated yet</p>
              <p style={{ fontSize: 13, color: 'var(--text-4)', margin: 0 }}>
                Run the generation script to populate:
              </p>
              <code style={{
                display: 'inline-block', marginTop: 12, padding: '8px 16px', borderRadius: 8,
                background: 'var(--bg-2)', color: '#7c3aed', fontSize: 12,
                border: '1px solid rgba(124,58,237,0.2)',
              }}>
                uv run python scripts/gen_qa.py --run
              </code>
            </div>
          </div>
        ) : (
          <QAExplorer initialData={topics} />
        )}
      </div>
    </div>
  );
}
