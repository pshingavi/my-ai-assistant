'use client';

export default function SkeletonCard() {
  return (
    <div className="w-full rounded-3xl overflow-hidden" style={{ boxShadow: '0 24px 80px rgba(0,0,0,0.1)' }}>
      {/* Hero: split layout matching ByteCardV2 */}
      <div className="flex" style={{ minHeight: 400, background: '#0f0a2e' }}>
        {/* Left: text */}
        <div className="flex-1 flex flex-col gap-6" style={{ padding: '36px 40px' }}>
          <div className="h-2.5 rounded-full shimmer w-1/4" style={{ background: 'rgba(196,181,253,0.12)' }} />
          <div className="w-16 h-16 rounded-2xl shimmer" style={{ background: 'rgba(124,58,237,0.15)' }} />
          <div className="space-y-3.5 flex-1">
            <div className="h-1.5 rounded-full shimmer w-1/6" style={{ background: 'rgba(167,139,250,0.15)' }} />
            <div className="h-5 rounded-xl shimmer w-full" style={{ background: 'rgba(255,255,255,0.07)' }} />
            <div className="h-5 rounded-xl shimmer w-4/5" style={{ background: 'rgba(255,255,255,0.05)' }} />
            <div className="h-5 rounded-xl shimmer w-3/5" style={{ background: 'rgba(255,255,255,0.04)' }} />
            <div className="h-5 rounded-xl shimmer w-4/6" style={{ background: 'rgba(255,255,255,0.03)' }} />
          </div>
          <div className="h-2.5 rounded-full shimmer w-1/3" style={{ background: 'rgba(167,139,250,0.12)' }} />
        </div>
        {/* Right: image placeholder */}
        <div className="hidden sm:block flex-shrink-0 shimmer" style={{ width: 260, background: 'rgba(124,58,237,0.08)' }} />
      </div>

      {/* Tab bar */}
      <div className="flex" style={{ background: 'var(--surface)', borderBottom: '2px solid var(--border)', height: 58 }}>
        {[60, 45, 55, 50].map((w, i) => (
          <div key={i} className="flex-1 flex items-center justify-center gap-2.5">
            <div className="h-4 w-4 rounded shimmer" style={{ background: 'rgba(124,58,237,0.07)' }} />
            <div className="h-3 rounded shimmer hidden sm:block" style={{ width: `${w - 15}%`, background: 'rgba(124,58,237,0.06)' }} />
          </div>
        ))}
      </div>

      {/* Content */}
      <div className="space-y-5" style={{ padding: '40px', background: 'var(--surface)', minHeight: 260 }}>
        <div className="flex items-center gap-4 mb-8">
          <div className="w-12 h-12 rounded-2xl shimmer" style={{ background: 'rgba(124,58,237,0.09)' }} />
          <div className="space-y-2.5 flex-1">
            <div className="h-3 rounded shimmer w-1/4" style={{ background: 'rgba(124,58,237,0.12)' }} />
            <div className="h-2.5 rounded shimmer w-1/6" style={{ background: 'rgba(124,58,237,0.07)' }} />
          </div>
        </div>
        <div className="rounded-2xl p-7 space-y-4" style={{ background: 'rgba(124,58,237,0.04)', border: '1px solid rgba(124,58,237,0.1)' }}>
          {[100, 95, 88, 78, 65].map((w, i) => (
            <div key={i} className="h-3 rounded-lg shimmer" style={{ width: `${w}%`, background: 'rgba(124,58,237,0.06)' }} />
          ))}
        </div>
      </div>
    </div>
  );
}

export function SkeletonBuildCard() {
  return (
    <div className="space-y-5 animate-pulse">
      <div className="flex items-center gap-3">
        <div className="h-8 w-8 rounded-xl shimmer" style={{ background: 'rgba(124,58,237,0.12)' }} />
        <div className="h-6 rounded-xl shimmer flex-1 max-w-xs" style={{ background: 'rgba(124,58,237,0.08)' }} />
        <div className="ml-auto h-6 w-20 rounded-full shimmer" style={{ background: 'rgba(124,58,237,0.08)' }} />
      </div>
      <div className="rounded-2xl overflow-hidden" style={{ background: '#0d0d1a', border: '1px solid rgba(139,92,246,0.18)' }}>
        <div className="h-9 shimmer" style={{ background: 'rgba(139,92,246,0.06)' }} />
        <div className="p-5 space-y-2.5">
          {[100, 85, 95, 70, 80].map((w, i) => (
            <div key={i} className="h-3 rounded shimmer" style={{ width: `${w}%`, background: 'rgba(139,92,246,0.08)' }} />
          ))}
        </div>
      </div>
      <div className="rounded-xl p-5 space-y-3" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
        <div className="h-3 rounded shimmer w-1/5" style={{ background: 'rgba(124,58,237,0.1)' }} />
        {[100, 90, 75].map((w, i) => (
          <div key={i} className="h-2.5 rounded shimmer" style={{ width: `${w}%`, background: 'rgba(124,58,237,0.05)' }} />
        ))}
      </div>
    </div>
  );
}
