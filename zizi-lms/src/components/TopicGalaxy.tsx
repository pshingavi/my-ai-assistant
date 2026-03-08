'use client';

import { useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import type { KGData } from '@/src/types';

interface SimNode {
  id: string;
  name: string;
  is_post: boolean;
  module_number?: string;
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
  relation?: string;
}

interface TopicGalaxyProps {
  data: KGData;
  height?: number;
}

export default function TopicGalaxy({ data, height = 600 }: TopicGalaxyProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const simRef = useRef<{ stop: () => void } | null>(null);
  const router = useRouter();

  const navigate = useCallback((id: string) => router.push(`/learn/${id}`), [router]);

  useEffect(() => {
    if (typeof window === 'undefined' || !svgRef.current || !data.nodes?.length) return;

    const W = containerRef.current?.clientWidth || 800;
    const H = height;

    const nodes: SimNode[] = data.nodes.map((n) => ({
      id: n.id,
      name: n.name,
      is_post: n.is_post,
      module_number: n.module_number,
    }));

    const nodeSet = new Set(nodes.map((n) => n.id));
    const links: SimLink[] = data.edges
      .filter((e) => nodeSet.has(e.source) && nodeSet.has(e.target))
      .map((e) => ({ source: e.source, target: e.target, relation: e.relation }));

    import('d3').then((d3) => {
      if (!svgRef.current) return;
      if (simRef.current) simRef.current.stop();

      const svg = d3.select(svgRef.current);
      svg.selectAll('*').remove();

      // Glow filters
      const defs = svg.append('defs');
      ['purple', 'cyan'].forEach((name) => {
        const f = defs.append('filter').attr('id', `glow-${name}-galaxy`);
        f.append('feGaussianBlur').attr('stdDeviation', '4').attr('result', 'blur');
        const merge = f.append('feMerge');
        merge.append('feMergeNode').attr('in', 'blur');
        merge.append('feMergeNode').attr('in', 'SourceGraphic');
      });

      // Zoom
      const zoom = d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.2, 5])
        .on('zoom', (ev) => g.attr('transform', ev.transform));
      svg.call(zoom).on('dblclick.zoom', null);

      const g = svg.append('g');

      const simulation = d3
        .forceSimulation<SimNode>(nodes)
        .force('link', d3.forceLink<SimNode, SimLink>(links).id((d) => d.id).distance(100).strength(0.5))
        .force('charge', d3.forceManyBody().strength(-200))
        .force('center', d3.forceCenter(W / 2, H / 2))
        .force('collision', d3.forceCollide(22))
        .alphaDecay(0.025);

      simRef.current = simulation;

      // Links
      const linkSel = g.append('g')
        .selectAll<SVGLineElement, SimLink>('line')
        .data(links)
        .join('line')
        .attr('stroke', (d) =>
          (d as SimLink).relation === 'BUILDS_ON'
            ? 'rgba(139,92,246,0.35)'
            : 'rgba(255,255,255,0.08)'
        )
        .attr('stroke-width', 1.2);

      // Node groups
      const nodeG = g.append('g')
        .selectAll<SVGGElement, SimNode>('g')
        .data(nodes)
        .join('g')
        .attr('cursor', 'pointer')
        .call(
          d3.drag<SVGGElement, SimNode>()
            .on('start', (ev, d) => { if (!ev.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
            .on('drag', (ev, d) => { d.fx = ev.x; d.fy = ev.y; })
            .on('end', (ev, d) => { if (!ev.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; })
        )
        .on('click', (_ev, d) => navigate(d.id));

      // Circles
      nodeG.append('circle')
        .attr('r', (d) => (d.is_post ? 5 : 8))
        .attr('fill', (d) => (d.is_post ? '#22d3ee' : '#8b5cf6'))
        .attr('opacity', 0.88)
        .attr('filter', (d) =>
          d.is_post ? 'url(#glow-cyan-galaxy)' : 'url(#glow-purple-galaxy)'
        );

      // Labels
      nodeG.append('text')
        .text((d) => d.name.length > 22 ? d.name.slice(0, 20) + '…' : d.name)
        .attr('text-anchor', 'middle')
        .attr('dy', (d) => (d.is_post ? 16 : 20))
        .attr('font-size', '10px')
        .attr('font-family', 'Inter, sans-serif')
        .attr('fill', '#94a3b8')
        .attr('pointer-events', 'none');

      // Hover
      nodeG
        .on('mouseenter', function (_ev, d) {
          d3.select(this).select('circle')
            .transition().duration(150)
            .attr('r', (d.is_post ? 5 : 8) * 1.6)
            .attr('opacity', 1);
          d3.select(this).select('text')
            .transition().duration(150)
            .attr('fill', '#f1f5f9').attr('font-size', '11px');
        })
        .on('mouseleave', function (_ev, d) {
          d3.select(this).select('circle')
            .transition().duration(150)
            .attr('r', d.is_post ? 5 : 8)
            .attr('opacity', 0.88);
          d3.select(this).select('text')
            .transition().duration(150)
            .attr('fill', '#94a3b8').attr('font-size', '10px');
        });

      simulation.on('tick', () => {
        linkSel
          .attr('x1', (d) => (d.source as SimNode).x ?? 0)
          .attr('y1', (d) => (d.source as SimNode).y ?? 0)
          .attr('x2', (d) => (d.target as SimNode).x ?? 0)
          .attr('y2', (d) => (d.target as SimNode).y ?? 0);
        nodeG.attr('transform', (d) => `translate(${d.x ?? 0},${d.y ?? 0})`);
      });
    });

    return () => { if (simRef.current) simRef.current.stop(); };
  }, [data, height, navigate]);

  return (
    <div
      ref={containerRef}
      className="w-full rounded-2xl overflow-hidden relative"
      style={{
        height,
        background: 'rgba(139,92,246,0.03)',
        border: '1px solid rgba(139,92,246,0.15)',
      }}
    >
      <svg ref={svgRef} className="w-full h-full" style={{ display: 'block' }} />
      {/* Legend */}
      <div
        className="absolute bottom-3 right-3 flex items-center gap-4 px-3 py-2 rounded-lg"
        style={{ background: 'rgba(10,10,15,0.85)', border: '1px solid rgba(139,92,246,0.2)' }}
      >
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full" style={{ background: '#8b5cf6' }} />
          <span className="text-xs" style={{ color: '#94a3b8' }}>Course topic</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full" style={{ background: '#22d3ee' }} />
          <span className="text-xs" style={{ color: '#94a3b8' }}>Post</span>
        </div>
        <span className="text-xs hidden sm:block" style={{ color: '#475569' }}>Scroll to zoom · Drag nodes</span>
      </div>
    </div>
  );
}
