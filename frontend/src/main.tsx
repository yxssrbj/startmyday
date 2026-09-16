import { StrictMode, useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Command, ArrowUpRight, Check, Sparkles } from 'lucide-react';
import './style.css';

type Status = 'pending' | 'in_progress' | 'completed';
type Task = {
  id: string; title: string; deliverable: string; first_action: string;
  completion_check: string; prerequisites: string[]; estimated_minutes: number;
  status: Status; ready: boolean;
};
type Project = { name?: string; tasks: Task[] };

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, options);
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data?.detail;
    throw new Error(typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map(d => typeof d === 'string' ? d : d.msg).join(' · ') : 'Could not connect to the backend. Check that FastAPI is running.');
  }
  return data;
}

function App() {
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState('');
  const [selected, setSelected] = useState<string | null>(null);
  const [minutesInput, setMinutesInput] = useState('30');
  const [availableMinutes, setAvailableMinutes] = useState(30);
  const [recommendedId, setRecommendedId] = useState<string | null>(null);
  const [recommendationLoaded, setRecommendationLoaded] = useState(false);
  const latestRequest = useRef(0);
  const validMinutes = Number.isSafeInteger(Number(minutesInput)) && Number(minutesInput) > 0;

  async function refresh(minutes = availableMinutes) {
    const requestId = ++latestRequest.current;
    setLoading(true); setError(''); setRecommendationLoaded(false);
    setRecommendedId(null);
    try {
      const [updatedProject, recommendation] = await Promise.all([
        request<Project>('/api/project'),
        request<Pick<Task, 'id'> | null>('/api/next-task?available_minutes=' + minutes),
      ]);
      if (requestId !== latestRequest.current) return;
      setProject(updatedProject);
      setRecommendedId(recommendation?.id ?? null);
      setRecommendationLoaded(true);
    }
    catch (e) {
      if (requestId === latestRequest.current) setError(e instanceof Error ? e.message : 'Could not load the plan.');
    }
    finally { if (requestId === latestRequest.current) setLoading(false); }
  }
  useEffect(() => { void refresh(); }, []);

  async function update(task: Task, status: Status) {
    setSaving(true); setError(''); setNotice('');
    try {
      setProject(await request<Project>('/api/tasks/' + encodeURIComponent(task.id) + '/progress', {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status }),
      }));
      setNotice('Progress saved for ' + task.title + '.');
      if (status === 'completed') setSelected(null);
      await refresh();
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not save progress.'); }
    finally { setSaving(false); }
  }

  const tasks = project?.tasks ?? [];
  const done = tasks.filter(t => t.status === 'completed').length;
  const ready = tasks.filter(t => t.ready);
  const focus = tasks.find(t => t.id === (selected ?? recommendedId));
  const busy = loading || saving;

  return <div className="shell">
    <header><a className="brand" href="/"><span className="sun"><Command aria-hidden="true" /></span> morning plan<span className="brand-dot">.</span></a><span className="header-note">A little direction. A real first step.</span></header>
    <main>
      <section className="intro"><div><p className="eyebrow">YOUR PROGRAMMING SPACE</p><h1>Make room for<br /><em>one good session.</em></h1><p className="subtitle">Pick up where you left off. Build something that matters.</p></div><div className="date-card"><span>YOUR PROJECT</span><strong>{project?.name || 'Morning Plan'}</strong><p>One piece at a time.</p></div></section>
      {error && <Alert variant="destructive" className="error"><AlertDescription>{error}</AlertDescription> <Button onClick={() => void refresh()} disabled={loading || saving}>Try again</Button></Alert>}
      <p className="sr-only" role="status">{notice}</p>
      {loading && !project ? <p role="status" className="empty">Opening your plan…</p> : project && <>
        <section className="overview" aria-label="Project progress"><div><strong>{done}<small> / {tasks.length}</small></strong><span>tasks completed</span></div><Progress className="progress-track" aria-label="Tasks completed" value={tasks.length ? done / tasks.length * 100 : 0} /><span className="ready-count">{ready.length} ready to work on</span></section>
        <form className="time-budget" onSubmit={event => {
          event.preventDefault();
          if (!validMinutes || busy) return;
          const minutes = Number(minutesInput);
          setAvailableMinutes(minutes);
          setSelected(null);
          void refresh(minutes);
        }}>
          <div><Label htmlFor="available-minutes">Available programming time</Label><p id="time-hint">Find a ready task that fits your session.</p></div>
          <div className="time-controls"><Input id="available-minutes" type="number" min="1" step="1" required value={minutesInput} onChange={event => setMinutesInput(event.target.value)} disabled={busy} aria-describedby="time-hint" /><span>minutes</span><Button type="submit" className="primary" disabled={busy || !validMinutes}>{loading ? 'Finding a task…' : 'Find my next task'}</Button></div>
        </form>
        {selected && <Button variant="ghost" size="sm" className="refresh back-to-recommendation" onClick={() => setSelected(null)}>Back to recommendation · {availableMinutes} minutes</Button>}
        <div className="workspace"><Card className="focus" role="region" aria-label="Selected task"><p className="eyebrow">{selected ? 'TASK DETAILS' : 'YOUR NEXT STEP'}</p>{focus ? <>
          <div className="task-meta"><Badge variant="secondary" className="pill">{focus.status === 'completed' ? 'Completed' : focus.ready ? 'Ready when you are' : 'Waiting on prerequisites'}</Badge><span>{focus.estimated_minutes} min estimate</span></div>
          <h2>{focus.title}</h2><p className="deliverable">{focus.deliverable}</p>
          <div className="instruction"><span className="step-number">01</span><div><h3>Start here</h3><p>{focus.first_action}</p></div></div>
          <div className="instruction"><span className="step-number">02</span><div><h3>You’re done when</h3><p>{focus.completion_check}</p></div></div>
          {!focus.ready && focus.status !== 'completed' && <p className="blocked">Finish first: {focus.prerequisites.filter(id => tasks.find(t => t.id === id)?.status !== 'completed').map(id => tasks.find(t => t.id === id)?.title ?? id).join(', ')}</p>}
          <div className="actions">{focus.status !== 'completed' ? <><Button className="primary" disabled={busy || !focus.ready} onClick={() => void update(focus, 'completed')}>{saving ? 'Saving…' : 'Mark completed'} <ArrowUpRight aria-hidden="true" /></Button>{focus.status === 'pending' && <Button variant="outline" className="secondary" disabled={busy || !focus.ready} onClick={() => void update(focus, 'in_progress')}>Start task</Button>}</> : <Button variant="outline" className="secondary" disabled={busy} onClick={() => void update(focus, 'pending')}>Reopen task</Button>}</div>
          <p className="footnote">Progress is saved on this laptop.</p>
        </> : <div className="empty"><h2>{loading ? 'Finding your next step…' : !recommendationLoaded ? 'Recommendation unavailable' : tasks.length && done === tasks.length ? 'A good place to pause.' : ready.length ? 'No task fits this session.' : 'No ready tasks yet.'}</h2><p>{loading ? 'Checking your available time and prerequisites.' : !recommendationLoaded ? 'Try again to get a recommendation from your plan.' : tasks.length && done === tasks.length ? 'Every task in this plan is complete. Review your work or add the next task to your project plan.' : ready.length ? 'No ready task fits within ' + availableMinutes + ' minutes. Try a longer session or review your tasks.' : 'Check the tasks and their prerequisites in your project plan.'}</p></div>}</Card>
        <aside><div className="list-heading"><h2>The build, step by step</h2><Button variant="ghost" size="sm" className="refresh" onClick={() => void refresh()} disabled={loading || saving}>{loading ? 'Loading…' : 'Refresh'}</Button></div><p className="list-caption">Each piece builds on the last.</p><div className="task-list">{tasks.map((task, index) => <Button variant="ghost" key={task.id} className={'task-row ' + (focus?.id === task.id ? 'selected' : '')} onClick={() => setSelected(task.id)} aria-pressed={focus?.id === task.id}><span className={'task-index ' + (task.status === 'completed' ? 'done' : '')}>{task.status === 'completed' ? <Check aria-hidden={true} /> : String(index + 1).padStart(2, '0')}</span><span><strong>{task.title}</strong><small>{task.status === 'completed' ? 'Completed' : task.ready ? task.status === 'in_progress' ? 'In progress' : 'Ready' : 'Blocked'}<span> · </span>{task.estimated_minutes} min</small></span><ArrowUpRight aria-hidden="true" /></Button>)}</div><div className="note"><Sparkles aria-hidden="true" /><p>You don’t need to finish the whole project today.<br /><strong>Just take the next clear step.</strong></p></div></aside></div>
      </>}
    </main><footer><span>MORNING PLAN / A WORK IN PROGRESS</span><span>Built by you, for your day.</span></footer>
  </div>;
}

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>);
