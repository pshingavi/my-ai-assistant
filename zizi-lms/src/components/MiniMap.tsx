'use client';

import { useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import type { TopicNeighbors, TopicSummary } from '@/src/types';

interface MiniMapProps {
  currentTopic: TopicSummary;
  neighbors: TopicNeighbors;
}

interface SimNode {
  id: string;
  name: string;
  isCurrent: boolean;
  isPost: boolean;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
}

interface SimLink {
  source: string | SimNode;
  target: string | SimNode;
}

export default function MiniMap({ currentTopic, neighbors }: MiniMapProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const simulationRef = useRef<{ stop: () => void } | null>(null);
  const router = useRouter();

  useEffect(() => {
    if (typeof window === 'undefined' || !svgRef.current) return;

    const allNeighbors: TopicSummary[] = [
      ...neighbors.prerequisites,
      ...neighbors.next,
      ...neighbors.related,
    ];

    // Build unique nodes
    const seen = new Set<string>();
    const nodes: SimNode[] = [];

    const addNode = (t: TopicSummary, isCurrent: boolean) => {
      if (!seen.has(t.id)) {
        seen.add(t.id);
        nodes.push({ id: t.id, name: t.name, isCurrent, isPost: t.is_post });
      }
    };

    addNode(currentTopic, true);
    allNeighbors.forEach((t) => addNode(t, false));

    const links: SimLink[] = [
      ...neighbors.prerequisites.map((t) => ({ source: t.id, target: currentTopic.id })),
      ...neighbors.next.map((t) => ({ source: currentTopic.id, target: t.id })),
      ...neighbors.related.map((t) => ({ source: currentTopic.id, target: t.id })),
    ].filter((l) => seen.has(l.source as string) && seen.has(l.target as string));

    const W = 160;
    const H = 160;

    import('d3').then((d3) => {
      if (!svgRef.current) return;

      // Stop any existing simulation
      if (simulationRef.current) simulationRef.current.stop();

      const svg = d3.select(svgRef.current);
      svg.selectAll('*').remove();

      const g = svg.append('g');

      const simulation = d3
        .forceSimulation<SimNode>(nodes)
        .force(
          'link',
          d3.forceLink<SimNode, SimLink>(links).id((d) => d.id).distance(45)
        )
        .force('charge', d3.forceManyBody().strength(-120))
        .force('center', d3.forceCenter(W / 2, H / 2))
        .force('collision', d3.forceCollide(14));

      simulationRef.current = simulation;

      // Fix current node at center
      const curr = nodes.find((n) => n.isCurrent);
      if (curr) {
        curr.fx = W / 2;
        curr.fy = H / 2;
      }

      const linkSel = g
        .append('g')
        .selectAll<SVGLineElement, SimLink>('line')
        .data(links)
        .join('line')
        .attr('stroke', 'rgba(139,92,246,0.3)')
        .attr('stroke-width', 1);

      const nodeSel = g
        .append('g')
        .selectAll<SVGCircleElement, SimNode>('circle')
        .data(nodes)
        .join('circle')
        .attr('r', (d) => (d.isCurrent ? 8 : 5))
        .attr('fill', (d) => {
          if (d.isCurrent) return '#ffffff';
          return d.isPost ? '#22d3ee' : '#8b5cf6';
        })
        .attr('cursor', (d) => (d.isCurrent ? 'default' : 'pointer'))
        .attr('opacity', (d) => (d.isCurrent ? 1 : 0.75))
        .style('filter', (d) =>
          d.isCurrent ? 'drop-shadow(0 0 6px white)' : 'none'
        )
        .on('click', (_event, d) => {
          if (!d.isCurrent) router.push(`/learn/${d.id}`);
        })
        .on('mouseenter', function (_event, d) {
          if (!d.isCurrent) {
            d3.select(this)
              .attr('opacity', 1)
              .style('filter', d.isPost
                ? 'drop-shadow(0 0 6px #22d3ee)'
                : 'drop-shadow(0 0 6px #8b5cf6)');
          }
        })
        .on('mouseleave', function (_event, d) {
          if (!d.isCurrent) {
            d3.select(this)
              .attr('opacity', 0.75)
              .style('filter', 'none');
          }
        });

      // Tooltips
      nodeSel.append('title').text((d) => d.name);

      simulation.on('tick', () => {
        linkSel
          .attr('x1', (d) => (d.source as SimNode).x ?? 0)
          .attr('y1', (d) => (d.source as SimNode).y ?? 0)
          .attr('x2', (d) => (d.target as SimNode).x ?? 0)
          .attr('y2', (d) => (d.target as SimNode).y ?? 0);

        nodeSel
          .attr('cx', (d) => Math.max(8, Math.min(W - 8, d.x ?? W / 2)))
          .attr('cy', (d) => Math.max(8, Math.min(H - 8, d.y ?? H / 2)));
      });
    });

    return () => {
      if (simulationRef.current) simulationRef.current.stop();
    };
  }, [currentTopic.id, neighbors, router]);

  return (
    <div className="w-40 shrink-0 hidden lg:flex flex-col gap-2">
      <p className="text-xs font-semibold text-center" style={{ color: '#475569' }}>
        Topic Map
      </p>
      <div
        className="rounded-xl overflow-hidden"
        style={{ border: '1px solid rgba(139,92,246,0.2)', background: 'rgba(139,92,246,0.04)' }}
      >
        <svg ref={svgRef} width={160} height={160} />
      </div>
      <div className="flex items-center gap-1.5 justify-center">
        <span className="w-2 h-2 rounded-full bg-white" style={{ boxShadow: '0 0 4px white' }} />
        <span className="text-xs" style={{ color: '#475569' }}>you are here</span>
      </div>
      <div className="flex items-center gap-3 justify-center flex-wrap">
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full" style={{ background: '#8b5cf6' }} />
          <span className="text-xs" style={{ color: '#475569' }}>topic</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full" style={{ background: '#22d3ee' }} />
          <span className="text-xs" style={{ color: '#475569' }}>post</span>
        </div>
      </div>
    </div>
  );
}
