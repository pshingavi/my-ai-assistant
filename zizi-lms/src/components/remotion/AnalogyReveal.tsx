import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion';
import type { AnalogyRevealProps } from '@/src/types';

export function AnalogyReveal({ concept, analogy, emoji, accentColor, keywords }: AnalogyRevealProps) {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Emoji bounce in at frame 0
  const emojiScale = spring({ frame, fps, config: { damping: 8, stiffness: 100 } });

  // Concept label fades in at frame 10
  const conceptOpacity = interpolate(frame, [10, 25], [0, 1], { extrapolateRight: 'clamp' });

  // Analogy words reveal one by one, starting at frame 20
  const words = analogy.split(' ');
  const wordsPerFrame = 0.4; // slightly slower than 0.5 for readability

  // Pulsing glow on background
  const glowOpacity = interpolate(frame, [0, durationInFrames / 2, durationInFrames], [0.3, 0.6, 0.3]);

  return (
    <AbsoluteFill style={{ background: '#07070d', fontFamily: 'Inter, sans-serif', overflow: 'hidden' }}>
      {/* Animated background glow */}
      <div style={{
        position: 'absolute', top: '-20%', left: '10%',
        width: 600, height: 600, borderRadius: '50%',
        background: `radial-gradient(circle, ${accentColor}33, transparent 70%)`,
        filter: 'blur(80px)',
        opacity: glowOpacity,
      }} />
      <div style={{
        position: 'absolute', bottom: '-20%', right: '10%',
        width: 500, height: 500, borderRadius: '50%',
        background: 'radial-gradient(circle, #22d3ee22, transparent 70%)',
        filter: 'blur(60px)',
        opacity: glowOpacity * 0.7,
      }} />

      <AbsoluteFill style={{
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        padding: '80px 120px', gap: 32,
      }}>
        {/* Emoji */}
        <div style={{ fontSize: 96, transform: `scale(${emojiScale})`, lineHeight: 1 }}>
          {emoji}
        </div>

        {/* Concept label */}
        <div style={{
          opacity: conceptOpacity,
          fontSize: 18, fontWeight: 700, letterSpacing: 4,
          textTransform: 'uppercase', color: accentColor,
        }}>
          {concept}
        </div>

        {/* Analogy text — word by word reveal */}
        <div style={{
          fontSize: 36, fontWeight: 700, lineHeight: 1.5,
          color: '#f1f5f9', textAlign: 'center', maxWidth: 900,
        }}>
          {words.map((word, i) => {
            const wordOpacity = interpolate(
              frame,
              [20 + i / wordsPerFrame, 25 + i / wordsPerFrame],
              [0, 1],
              { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' }
            );
            const wordY = interpolate(
              frame,
              [20 + i / wordsPerFrame, 25 + i / wordsPerFrame],
              [12, 0],
              { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' }
            );
            // highlight keywords
            const isKeyword = keywords?.some(k => word.toLowerCase().includes(k.toLowerCase()));
            return (
              <span key={i} style={{
                opacity: wordOpacity,
                transform: `translateY(${wordY}px)`,
                display: 'inline-block',
                color: isKeyword ? accentColor : '#f1f5f9',
                marginRight: 8,
              }}>
                {word}
              </span>
            );
          })}
        </div>

        {/* Bottom bar */}
        <div style={{
          position: 'absolute', bottom: 40, left: 120, right: 120,
          height: 1,
          background: `linear-gradient(90deg, transparent, ${accentColor}88, transparent)`,
          opacity: interpolate(frame, [40, 60], [0, 1], { extrapolateRight: 'clamp' }),
        }} />
        <div style={{
          position: 'absolute', bottom: 20, right: 120,
          fontSize: 13, color: '#334155', fontStyle: 'italic',
          opacity: interpolate(frame, [60, 80], [0, 1], { extrapolateRight: 'clamp' }),
        }}>
          Zizi Byte · Learn in bytes. Think in leaps.
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
}
