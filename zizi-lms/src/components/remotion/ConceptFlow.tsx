import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';
import type { ConceptFlowProps } from '@/src/types';

export function ConceptFlow({ concept, nodes, edges, accentColor }: ConceptFlowProps) {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  return (
    <AbsoluteFill style={{ background: '#07070d', fontFamily: 'Inter, sans-serif' }}>
      {/* Background grid */}
      <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', opacity: 0.04 }}>
        <defs>
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#8b5cf6" strokeWidth="0.5" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
      </svg>

      {/* Title */}
      <div style={{
        position: 'absolute', top: 40, left: 0, right: 0,
        textAlign: 'center', fontSize: 20, fontWeight: 700,
        color: accentColor, letterSpacing: 3, textTransform: 'uppercase',
        opacity: interpolate(frame, [0, 20], [0, 1], { extrapolateRight: 'clamp' }),
      }}>
        {concept}
      </div>

      {/* Edges (render before nodes so nodes appear on top) */}
      <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
        {edges.map((edge, i) => {
          const fromNode = nodes.find(n => n.id === edge.fromId);
          const toNode = nodes.find(n => n.id === edge.toId);
          if (!fromNode || !toNode) return null;
          const x1 = (fromNode.x / 100) * width;
          const y1 = (fromNode.y / 100) * height;
          const x2 = (toNode.x / 100) * width;
          const y2 = (toNode.y / 100) * height;
          const edgeProgress = spring({ frame: frame - (i * 8 + 20), fps, config: { damping: 20 } });
          const midX = (x1 + x2) / 2;
          const midY = (y1 + y2) / 2;
          return (
            <g key={`edge-${i}`} style={{ opacity: edgeProgress }}>
              <defs>
                <marker id={`arrow-${i}`} markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
                  <path d="M0,0 L0,6 L8,3 z" fill={accentColor} opacity="0.8" />
                </marker>
              </defs>
              <line x1={x1} y1={y1} x2={x2} y2={y2}
                stroke={accentColor} strokeWidth="1.5" strokeOpacity="0.5"
                strokeDasharray="4 4"
                markerEnd={`url(#arrow-${i})`}
              />
              {edge.label && (
                <text x={midX} y={midY - 8} textAnchor="middle"
                  fontSize="12" fill="#94a3b8" fontFamily="Inter, sans-serif">
                  {edge.label}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      {/* Nodes */}
      {nodes.map((node, i) => {
        const nodeSpring = spring({ frame: frame - i * 6, fps, config: { damping: 10, stiffness: 80 } });
        const cx = (node.x / 100) * width;
        const cy = (node.y / 100) * height;
        return (
          <div key={node.id} style={{
            position: 'absolute',
            left: cx - 70, top: cy - 28,
            width: 140, height: 56,
            transform: `scale(${nodeSpring})`,
            background: `linear-gradient(135deg, ${node.color}22, ${node.color}11)`,
            border: `1px solid ${node.color}66`,
            borderRadius: 12,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: `0 0 20px ${node.color}33`,
          }}>
            <span style={{ color: '#f1f5f9', fontSize: 13, fontWeight: 600, textAlign: 'center', padding: '0 8px' }}>
              {node.label}
            </span>
          </div>
        );
      })}

      {/* Footer */}
      <div style={{
        position: 'absolute', bottom: 20, right: 40,
        fontSize: 12, color: '#334155', fontStyle: 'italic',
        opacity: interpolate(frame, [30, 50], [0, 1], { extrapolateRight: 'clamp' }),
      }}>
        Zizi Byte · Learn in bytes. Think in leaps.
      </div>
    </AbsoluteFill>
  );
}
