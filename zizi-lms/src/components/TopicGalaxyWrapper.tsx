'use client';

import dynamic from 'next/dynamic';
import type { KGData } from '@/src/types';

const TopicGalaxy = dynamic(() => import('./TopicGalaxy'), { ssr: false });

export default function TopicGalaxyWrapper({ data }: { data: KGData }) {
  return <TopicGalaxy data={data} />;
}
