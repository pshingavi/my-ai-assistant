'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { fetchTopics } from '@/src/lib/api';

export default function LearnRedirect() {
  const router = useRouter();
  const [err, setErr] = useState('');

  useEffect(() => {
    fetchTopics()
      .then((topics) => {
        const first = topics.filter((t) => !t.is_post)[0] || topics[0];
        if (first) router.replace(`/learn/${first.id}`);
        else setErr('No topics found. Run the ingest script first.');
      })
      .catch(() => setErr('API server not reachable — start with: uv run python api_server.py'));
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-screen" style={{ background: '#0a0a0f' }}>
      {err ? (
        <p className="text-sm text-center" style={{ color: '#64748b' }}>{err}</p>
      ) : (
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-t-transparent animate-spin"
            style={{ borderColor: '#8b5cf6', borderTopColor: 'transparent' }} />
          <p className="text-xs" style={{ color: '#475569' }}>Loading first topic…</p>
        </div>
      )}
    </div>
  );
}
