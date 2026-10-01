import { useEffect, useMemo, useState } from 'react';
import { BookOpenText, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

type ConceptNode = { id: number; name: string; created_at: string };
type ConceptEdge = { source: number; target: number; shared_task_count: number };
type Graph = { nodes: ConceptNode[]; edges: ConceptEdge[] };
type PlacedNode = ConceptNode & { x: number; y: number };

function placeNodes(nodes: ConceptNode[]): PlacedNode[] {
  const ordered = [...nodes].sort((a, b) => a.id - b.id);
  return ordered.map((node, index) => {
    // Stagger the rings so connections do not all cross the same point.
    const ring = index < 8 ? 0 : index < 20 ? 1 : 2 + Math.floor((index - 20) / 16);
    const start = ring === 0 ? 0 : ring === 1 ? 8 : 20 + (ring - 2) * 16;
    const count = ring === 0 ? Math.min(8, ordered.length) : ring === 1 ? Math.min(12, ordered.length - 8) : Math.min(16, ordered.length - start);
    const angle = -Math.PI / 2 + (index - start + ring * 0.27) * 2 * Math.PI / count;
    const radius = ring === 0 ? ordered.length <= 8 ? 295 : 145 : ring === 1 ? 275 : 380;
    return { ...node, x: 500 + Math.cos(angle) * radius, y: 280 + Math.sin(angle) * radius * 0.59 };
  });
}

export function KnowledgeGraph() {
  const [graph, setGraph] = useState<Graph | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setLoading(true); setError('');
      try {
        const response = await fetch('/api/concepts', { signal: controller.signal });
        const data = await response.json().catch(() => null);
        if (!response.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : 'Could not load your concepts.');
        if (!data || !Array.isArray(data.nodes) || !Array.isArray(data.edges)) throw new Error('The concept graph response is incomplete.');
        setGraph(data);
      } catch (cause) {
        if (controller.signal.aborted) return;
        setError(cause instanceof Error ? cause.message : 'Could not load your concepts.');
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [retry]);

  const placed = useMemo(() => placeNodes(graph?.nodes ?? []), [graph]);
  const positions = new Map(placed.map(node => [node.id, node]));
  const selected = graph?.nodes.find(node => node.id === selectedId) ?? null;
  const connections = selected ? (graph?.edges ?? [])
    .filter(edge => edge.source === selected.id || edge.target === selected.id)
    .map(edge => ({ node: positions.get(edge.source === selected.id ? edge.target : edge.source), count: edge.shared_task_count }))
    .filter((item): item is { node: PlacedNode; count: number } => Boolean(item.node))
    .sort((a, b) => b.count - a.count || a.node.name.localeCompare(b.node.name)) : [];

  return <section className="knowledge-page" aria-labelledby="knowledge-title">
    <div className="knowledge-heading"><div><p className="eyebrow">YOUR LEARNING MAP</p><h2 id="knowledge-title">Concepts you have used together</h2><p>Each concept comes from a finished focus session. A line means you used both concepts while working on the same task.</p></div><Button variant="outline" size="sm" onClick={() => setRetry(value => value + 1)} disabled={loading}><RefreshCw aria-hidden="true" /> Refresh</Button></div>
    {error ? <Card className="knowledge-message" role="alert"><p>{error}</p><Button variant="outline" onClick={() => setRetry(value => value + 1)}>Try again</Button></Card> : loading ? <Card className="knowledge-message" role="status">Loading your learning map…</Card> : !graph?.nodes.length ? <Card className="knowledge-message"><BookOpenText aria-hidden="true" /><h3>No concepts yet</h3><p>Finish a focus session and add the concepts you used. They will appear here automatically.</p></Card> : <div className="knowledge-layout">
      <Card className="knowledge-canvas">
        <div className="knowledge-canvas-head"><span>{graph.nodes.length} {graph.nodes.length === 1 ? 'concept' : 'concepts'}</span><span>{graph.edges.length} {graph.edges.length === 1 ? 'connection' : 'connections'}</span></div>
        <svg viewBox="0 0 1000 560" role="img" aria-label={`Knowledge graph with ${graph.nodes.length} concepts and ${graph.edges.length} connections`}>
          {graph.edges.map(edge => {
            const source = positions.get(edge.source); const target = positions.get(edge.target);
            if (!source || !target) return null;
            const highlighted = selectedId === edge.source || selectedId === edge.target;
            return <line key={`${edge.source}-${edge.target}`} className={'knowledge-edge' + (highlighted ? ' highlighted' : '')} x1={source.x} y1={source.y} x2={target.x} y2={target.y} strokeWidth={Math.min(1.5 + edge.shared_task_count, 5)} />;
          })}
          {placed.map(node => {
            const active = node.id === selectedId;
            const connected = connections.some(item => item.node.id === node.id);
            return <g key={node.id} className={'knowledge-node' + (active ? ' selected' : '') + (connected ? ' connected' : '')} transform={`translate(${node.x} ${node.y})`} onClick={() => setSelectedId(node.id)} role="button" tabIndex={0} aria-label={`Select ${node.name}`} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); setSelectedId(node.id); } }}>
              <circle r="47" /><text textAnchor="middle" dominantBaseline="central">{node.name.length > 13 ? node.name.slice(0, 11) + '…' : node.name}</text><title>{node.name}</title>
            </g>;
          })}
        </svg>
        <p className="knowledge-caption">Select a concept to see what you used it with. Line weight reflects the number of shared tasks.</p>
      </Card>
      <Card className="knowledge-detail">
        {selected ? <><p className="eyebrow">SELECTED CONCEPT</p><h3>{selected.name}</h3><p className="knowledge-detail-copy">{connections.length ? `Used with ${connections.length} other ${connections.length === 1 ? 'concept' : 'concepts'}.` : 'No shared-task connections yet. This concept is still part of your map.'}</p><div className="knowledge-neighbors">{connections.map(({ node, count }) => <button key={node.id} type="button" onClick={() => setSelectedId(node.id)}><span>{node.name}</span><small>{count} shared {count === 1 ? 'task' : 'tasks'}</small></button>)}</div></> : <><p className="eyebrow">EXPLORE YOUR WORK</p><h3>Pick a concept</h3><p className="knowledge-detail-copy">See which ideas have appeared together in your tasks. These links show use, not mastery or understanding.</p></>}
        <div className="knowledge-index"><h4>All concepts</h4><div>{graph.nodes.map(node => <button key={node.id} type="button" className={selectedId === node.id ? 'active' : ''} aria-pressed={selectedId === node.id} onClick={() => setSelectedId(node.id)}>{node.name}</button>)}</div></div>
      </Card>
    </div>}
  </section>;
}
