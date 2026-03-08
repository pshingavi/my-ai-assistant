'use client';

export default function SkeletonCard() {
  return (
    <div className="glass-card p-6 space-y-5 animate-pulse">
      {/* Emoji placeholder */}
      <div className="flex items-center gap-3">
        <div className="w-14 h-14 rounded-2xl shimmer" style={{ background: 'rgba(139,92,246,0.1)' }} />
        <div className="space-y-2 flex-1">
          <div className="h-5 rounded-lg shimmer w-3/4" style={{ background: 'rgba(255,255,255,0.06)' }} />
          <div className="h-4 rounded-lg shimmer w-1/2" style={{ background: 'rgba(255,255,255,0.04)' }} />
        </div>
      </div>

      {/* Analogy section */}
      <div className="rounded-xl p-4 space-y-2" style={{ background: 'rgba(139,92,246,0.08)', border: '1px solid rgba(139,92,246,0.15)' }}>
        <div className="h-4 rounded shimmer w-1/3" style={{ background: 'rgba(139,92,246,0.2)' }} />
        <div className="h-3 rounded shimmer w-full" style={{ background: 'rgba(255,255,255,0.05)' }} />
        <div className="h-3 rounded shimmer w-5/6" style={{ background: 'rgba(255,255,255,0.05)' }} />
        <div className="h-3 rounded shimmer w-4/6" style={{ background: 'rgba(255,255,255,0.05)' }} />
      </div>

      {/* Explanation section */}
      <div className="rounded-xl p-4 space-y-2" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
        <div className="h-4 rounded shimmer w-1/4" style={{ background: 'rgba(255,255,255,0.08)' }} />
        <div className="h-3 rounded shimmer w-full" style={{ background: 'rgba(255,255,255,0.05)' }} />
        <div className="h-3 rounded shimmer w-full" style={{ background: 'rgba(255,255,255,0.05)' }} />
        <div className="h-3 rounded shimmer w-3/4" style={{ background: 'rgba(255,255,255,0.05)' }} />
      </div>

      {/* Why it matters */}
      <div className="rounded-xl p-4 space-y-2" style={{ background: 'rgba(34,211,238,0.05)', border: '1px solid rgba(34,211,238,0.1)' }}>
        <div className="h-4 rounded shimmer w-1/3" style={{ background: 'rgba(34,211,238,0.15)' }} />
        <div className="h-3 rounded shimmer w-full" style={{ background: 'rgba(255,255,255,0.05)' }} />
        <div className="h-3 rounded shimmer w-2/3" style={{ background: 'rgba(255,255,255,0.05)' }} />
      </div>

      {/* Sources */}
      <div className="flex gap-2 flex-wrap">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-6 rounded-full shimmer"
            style={{ width: `${60 + i * 20}px`, background: 'rgba(255,255,255,0.06)' }}
          />
        ))}
      </div>
    </div>
  );
}

export function SkeletonBuildCard() {
  return (
    <div className="glass-card p-6 space-y-5 animate-pulse">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="h-6 w-6 rounded shimmer" style={{ background: 'rgba(139,92,246,0.2)' }} />
        <div className="h-5 rounded shimmer w-1/2" style={{ background: 'rgba(255,255,255,0.06)' }} />
        <div className="ml-auto h-6 w-20 rounded-full shimmer" style={{ background: 'rgba(139,92,246,0.15)' }} />
      </div>

      {/* Code block */}
      <div className="rounded-xl p-4 space-y-2" style={{ background: '#0d0d14', border: '1px solid rgba(255,255,255,0.06)' }}>
        {[1, 2, 3, 4, 5, 6, 7].map((i) => (
          <div
            key={i}
            className="h-3 rounded shimmer"
            style={{
              width: `${30 + Math.random() * 60}%`,
              background: 'rgba(255,255,255,0.04)',
            }}
          />
        ))}
      </div>

      {/* Explanation */}
      <div className="space-y-2">
        <div className="h-4 rounded shimmer w-1/4" style={{ background: 'rgba(255,255,255,0.08)' }} />
        <div className="h-3 rounded shimmer w-full" style={{ background: 'rgba(255,255,255,0.05)' }} />
        <div className="h-3 rounded shimmer w-5/6" style={{ background: 'rgba(255,255,255,0.05)' }} />
      </div>

      {/* Run notes */}
      <div className="rounded-xl p-4 space-y-2" style={{ background: 'rgba(34,211,238,0.05)', border: '1px solid rgba(34,211,238,0.1)' }}>
        <div className="h-4 rounded shimmer w-1/3" style={{ background: 'rgba(34,211,238,0.15)' }} />
        <div className="h-3 rounded shimmer w-full" style={{ background: 'rgba(255,255,255,0.05)' }} />
      </div>
    </div>
  );
}
