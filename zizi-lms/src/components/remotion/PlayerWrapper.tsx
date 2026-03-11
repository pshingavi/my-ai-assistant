'use client';

import { Player } from '@remotion/player';
import { AnalogyReveal } from './AnalogyReveal';
import { ConceptFlow } from './ConceptFlow';
import type { RemotionCompositionProps } from '@/src/types';

interface Props {
  animationProps: RemotionCompositionProps;
}

export default function PlayerWrapper({ animationProps }: Props) {
  if (!animationProps || animationProps.type === 'none') return null;

  if (animationProps.type === 'analogy_reveal') {
    const props = animationProps.props;
    return (
      <Player
        component={AnalogyReveal}
        inputProps={{
          ...props,
          accentColor: props.accentColor || '#8b5cf6',
          keywords: props.keywords || [],
        }}
        durationInFrames={150}
        fps={30}
        compositionWidth={1280}
        compositionHeight={720}
        style={{ width: '100%', borderRadius: 16 }}
        controls
        loop
        autoPlay
      />
    );
  }

  if (animationProps.type === 'concept_flow') {
    const props = animationProps.props;
    return (
      <Player
        component={ConceptFlow}
        inputProps={{
          ...props,
          accentColor: props.accentColor || '#22d3ee',
        }}
        durationInFrames={180}
        fps={30}
        compositionWidth={1280}
        compositionHeight={720}
        style={{ width: '100%', borderRadius: 16 }}
        controls
        loop
        autoPlay
      />
    );
  }

  return null;
}
