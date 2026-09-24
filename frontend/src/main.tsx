import { StrictMode, useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { MorningSchedule, type ScheduleBlock } from '@/components/morning-schedule';
import { TaskNote } from '@/components/task-note';
import { ActivityHeatmap } from '@/components/activity-heatmap';
import { Mountain, ArrowUpRight, Check, Sparkles, Play, Square, Timer } from 'lucide-react';
import './style.css';

type Status = 'pending' | 'in_progress' | 'completed';
type Task = {
  id: string; title: string; deliverable: string; first_action: string;
  completion_check: string; prerequisites: string[]; estimated_minutes: number;
  status: Status; ready: boolean;
};
type Project = { name?: string; tasks: Task[] };
type MorningInput = {
  date: string; morningStart: string; workStart: string;
  routineMinutes: string; gymMinutes: string; bufferMinutes: string;
};
type MorningPlan = {
  programming_minutes: number; overbooked_minutes: number;
  task: Pick<Task, 'id'> | null;
  schedule: ScheduleBlock[];
};
type Preferences = {
  morning_start: string; work_start: string;
  routine_minutes: number; gym_minutes: number; buffer_minutes: number;
};
type WorkSession = {
  session_id: number; task_id: string; worked_on: string;
  start_time: string; end_time: string | null; actual_minutes: number | null;
};

function localDate() {
  const today = new Date();
  return [today.getFullYear(), String(today.getMonth() + 1).padStart(2, '0'), String(today.getDate()).padStart(2, '0')].join('-');
}

function formatElapsed(seconds: number) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor(seconds % 3600 / 60);
  const remainingSeconds = seconds % 60;
  return [hours, minutes, remainingSeconds].map(value => String(value).padStart(2, '0')).join(':');
}

function preferencesFrom(input: MorningInput): Preferences {
  return {
    morning_start: input.morningStart, work_start: input.workStart,
    routine_minutes: Number(input.routineMinutes), gym_minutes: Number(input.gymMinutes),
    buffer_minutes: Number(input.bufferMinutes),
  };
}

function initialMorning(): MorningInput {
  const today = new Date();
  const date = [today.getFullYear(), String(today.getMonth() + 1).padStart(2, '0'), String(today.getDate()).padStart(2, '0')].join('-');
  return { date, morningStart: '10:00', workStart: '15:00', routineMinutes: '60', gymMinutes: '90', bufferMinutes: '30' };
}

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
  const [savingPreferences, setSavingPreferences] = useState(false);
  const [preferencesError, setPreferencesError] = useState('');
  const [preferencesMessage, setPreferencesMessage] = useState('');
  const [preferencesLoaded, setPreferencesLoaded] = useState(false);
  const initializationId = useRef(0);
  const [noteLocked, setNoteLocked] = useState(false);
  const [notice, setNotice] = useState('');
  const [selected, setSelected] = useState<string | null>(null);
  const [morningInput, setMorningInput] = useState<MorningInput>(initialMorning);
  const [appliedMorning, setAppliedMorning] = useState<MorningInput>(initialMorning);
  const [morningPlan, setMorningPlan] = useState<MorningPlan | null>(null);
  const [recommendedId, setRecommendedId] = useState<string | null>(null);
  const [recommendationLoaded, setRecommendationLoaded] = useState(false);
  const [activeSession, setActiveSession] = useState<WorkSession | null>(null);
  const [sessionLoading, setSessionLoading] = useState(true);
  const [sessionSaving, setSessionSaving] = useState(false);
  const [sessionError, setSessionError] = useState('');
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [showFinish, setShowFinish] = useState(false);
  const [finishMinutes, setFinishMinutes] = useState('1');
  const [activityVersion, setActivityVersion] = useState(0);
  const latestRequest = useRef(0);
  const validMorning = Boolean(morningInput.date && morningInput.morningStart && morningInput.workStart)
    && [morningInput.routineMinutes, morningInput.gymMinutes, morningInput.bufferMinutes]
      .every(value => value.trim() !== '' && Number.isSafeInteger(Number(value)) && Number(value) >= 0);
  const hasChanges = JSON.stringify(morningInput) !== JSON.stringify(appliedMorning);
  const availableMinutes = morningPlan?.programming_minutes ?? 0;
  function setMorningField(field: keyof MorningInput, value: string) {
    setPreferencesMessage(''); setMorningInput(current => ({ ...current, [field]: value }));
  }

  async function refresh(input = appliedMorning) {
    const requestId = ++latestRequest.current;
    setLoading(true); setError(''); setRecommendationLoaded(false);
    setRecommendedId(null); setMorningPlan(null);
    try {
      const [updatedProject, recommendation] = await Promise.all([
        request<Project>('/api/project'),
        request<MorningPlan>('/api/morning-plan', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            morning_start: input.date + 'T' + input.morningStart + ':00',
            work_start: input.date + 'T' + input.workStart + ':00',
            routine_minutes: Number(input.routineMinutes),
            gym_minutes: Number(input.gymMinutes),
            buffer_minutes: Number(input.bufferMinutes),
          }),
        }),
      ]);
      if (requestId !== latestRequest.current) return;
      setProject(updatedProject);
      setMorningPlan(recommendation);
      setRecommendedId(recommendation.task?.id ?? null);
      setRecommendationLoaded(true);
    }
    catch (e) {
      if (requestId === latestRequest.current) setError(e instanceof Error ? e.message : 'Could not load the plan.');
    }
    finally { if (requestId === latestRequest.current) setLoading(false); }
  }
  async function initializePreferences() {
    const id = ++initializationId.current;
    setLoading(true); setPreferencesError('');
    try {
      const preferences = await request<Preferences>('/api/preferences');
      if (id !== initializationId.current) return;
      const input = {
        ...initialMorning(),
        morningStart: preferences.morning_start, workStart: preferences.work_start,
        routineMinutes: String(preferences.routine_minutes),
        gymMinutes: String(preferences.gym_minutes), bufferMinutes: String(preferences.buffer_minutes),
      };
      setMorningInput(input); setAppliedMorning(input); setPreferencesLoaded(true);
      await refresh(input);
    } catch (error) {
      if (id !== initializationId.current) return;
      setPreferencesError(error instanceof Error ? error.message : 'Could not load your preferences.');
      setLoading(false);
    }
  }
  async function loadActiveSession() {
    setSessionLoading(true); setSessionError('');
    try {
      setActiveSession(await request<WorkSession | null>('/api/sessions/active'));
    } catch (error) {
      setSessionError(error instanceof Error ? error.message : 'Could not load the active session.');
    } finally { setSessionLoading(false); }
  }
  useEffect(() => {
    void initializePreferences();
    void loadActiveSession();
    return () => { initializationId.current++; latestRequest.current++; };
  }, []);

  useEffect(() => {
    if (!activeSession) { setElapsedSeconds(0); return; }
    const updateElapsed = () => setElapsedSeconds(Math.max(0, Math.floor((Date.now() - new Date(activeSession.start_time).getTime()) / 1000)));
    updateElapsed();
    const timerId = window.setInterval(updateElapsed, 1000);
    return () => window.clearInterval(timerId);
  }, [activeSession]);

  async function saveDefaults() {
    if (!validMorning || busy) return;
    setSavingPreferences(true); setPreferencesError(''); setPreferencesMessage('');
    try {
      await request<Preferences>('/api/preferences', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(preferencesFrom(morningInput)),
      });
      setPreferencesMessage('Defaults saved. These times and durations will load next time; the date will be today.');
    } catch (error) {
      setPreferencesError(error instanceof Error ? error.message : 'Could not save your preferences.');
    } finally { setSavingPreferences(false); }
  }

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

  async function startSession(task: Task) {
    if (busy || activeSession) return;
    setSessionSaving(true); setSessionError(''); setNotice('');
    try {
      const session = await request<WorkSession>('/api/tasks/' + encodeURIComponent(task.id) + '/sessions/start', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ worked_on: localDate() }),
      });
      setActiveSession(session);
      setNotice('Focus session started for ' + task.title + '.');
    } catch (error) {
      setSessionError(error instanceof Error ? error.message : 'Could not start the focus session.');
      await loadActiveSession();
    } finally { setSessionSaving(false); }
  }

  function openFinishSession() {
    setFinishMinutes(String(Math.max(1, Math.round(elapsedSeconds / 60))));
    setShowFinish(true); setSessionError('');
  }

  async function finishSession() {
    if (!activeSession || sessionSaving) return;
    const minutes = Number(finishMinutes);
    if (!Number.isSafeInteger(minutes) || minutes <= 0) {
      setSessionError('Enter the number of focused minutes as a positive whole number.');
      return;
    }
    setSessionSaving(true); setSessionError(''); setNotice('');
    try {
      await request<WorkSession>('/api/sessions/' + activeSession.session_id + '/finish', {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ minutes }),
      });
      const taskTitle = project?.tasks.find(task => task.id === activeSession.task_id)?.title ?? activeSession.task_id;
      setActiveSession(null); setShowFinish(false);
      setActivityVersion(version => version + 1);
      setNotice('Saved ' + minutes + ' focused minutes for ' + taskTitle + '.');
    } catch (error) {
      setSessionError(error instanceof Error ? error.message : 'Could not finish the focus session.');
      await loadActiveSession();
    } finally { setSessionSaving(false); }
  }

  const tasks = project?.tasks ?? [];
  const done = tasks.filter(t => t.status === 'completed').length;
  const ready = tasks.filter(t => t.ready);
  const focus = tasks.find(t => t.id === (selected ?? recommendedId));
  const activeTask = tasks.find(task => task.id === activeSession?.task_id);
  const busy = loading || saving || savingPreferences || sessionLoading || sessionSaving || noteLocked;

  return <div className="shell">
    <header><a className="brand" href="/"><span className="sun"><Mountain aria-hidden="true" /></span><span>morning plan</span><span className="brand-dot">.</span></a><span className="header-note">A little direction. A real first step.</span></header>
    <main>
      <section className="intro"><div><p className="eyebrow">YOUR PROGRAMMING SPACE</p><h1>Make room for<br /><em>one good session.</em></h1><p className="subtitle">Pick up where you left off. Build something that matters.</p></div><div className="date-card"><span>YOUR PROJECT</span><strong>{project?.name || 'Morning Plan'}</strong><p>One piece at a time.</p></div></section>
      {error && <Alert variant="destructive" className="error"><AlertDescription>{error}</AlertDescription> <Button onClick={() => void refresh()} disabled={busy}>Try again</Button></Alert>}
      {preferencesError && <Alert variant="destructive"><AlertDescription>{preferencesError}</AlertDescription>{!preferencesLoaded && <Button variant="outline" onClick={() => void initializePreferences()} disabled={loading}>Retry loading defaults</Button>}</Alert>}
      {sessionError && <Alert variant="destructive" className="error"><AlertDescription>{sessionError}</AlertDescription></Alert>}
      <p className="sr-only" role="status">{notice}</p>
      {loading && !project ? <p role="status" className="empty">Opening your plan…</p> : project && <>
        <section className="overview" aria-label="Project progress"><div><strong>{done}<small> / {tasks.length}</small></strong><span>tasks completed</span></div><Progress className="progress-track" aria-label="Tasks completed" value={tasks.length ? done / tasks.length * 100 : 0} /><span className="ready-count">{ready.length} ready to work on</span></section>
        <form className="morning-form" onSubmit={event => {
          event.preventDefault();
          if (!validMorning || busy) return;
          setAppliedMorning({ ...morningInput });
          setSelected(null);
          void refresh(morningInput);
        }}>
          <div className="morning-form-heading"><div><h2>Plan your morning</h2><p>Reserve time for your day. Use what remains for programming.</p></div><Badge variant="outline">Local time · same day</Badge></div>
          <div className="morning-fields">
            <div><Label htmlFor="plan-date">Date</Label><Input id="plan-date" type="date" required value={morningInput.date} disabled={busy} onChange={event => setMorningField('date', event.target.value)} /></div>
            <div><Label htmlFor="morning-start">Morning starts</Label><Input id="morning-start" type="time" required value={morningInput.morningStart} disabled={busy} onChange={event => setMorningField('morningStart', event.target.value)} /></div>
            <div><Label htmlFor="work-start">Work starts</Label><Input id="work-start" type="time" required value={morningInput.workStart} disabled={busy} onChange={event => setMorningField('workStart', event.target.value)} /></div>
            <div><Label htmlFor="routine-minutes">Routine (minutes)</Label><Input id="routine-minutes" type="number" min="0" step="1" required value={morningInput.routineMinutes} disabled={busy} onChange={event => setMorningField('routineMinutes', event.target.value)} /><p>Walk, breakfast, and getting ready.</p></div>
            <div><Label htmlFor="gym-minutes">Gym (minutes)</Label><Input id="gym-minutes" type="number" min="0" step="1" required value={morningInput.gymMinutes} disabled={busy} onChange={event => setMorningField('gymMinutes', event.target.value)} /><p>Include travel and your shower.</p></div>
            <div><Label htmlFor="buffer-minutes">Before-work buffer (minutes)</Label><Input id="buffer-minutes" type="number" min="0" step="1" required value={morningInput.bufferMinutes} disabled={busy} onChange={event => setMorningField('bufferMinutes', event.target.value)} /><p>Leave room before your shift.</p></div>
          </div>
          <div className="morning-form-footer"><p>{hasChanges ? 'Changes not applied yet. Recalculate to update the result below.' : 'Adjust these starting estimates to match your day.'}</p><div className="preferences-actions"><Button type="button" variant="outline" disabled={busy || !validMorning} onClick={() => void saveDefaults()}>{savingPreferences ? 'Saving defaults...' : 'Save as defaults'}</Button><Button type="submit" disabled={busy || !validMorning}>{loading ? 'Planning…' : 'Plan my morning'}</Button></div></div>
          <p className="preferences-status" role="status">{preferencesMessage}</p>
        </form>
        {morningPlan && <section className={'budget-result ' + (morningPlan.overbooked_minutes > 0 ? 'overbooked' : '')} role="status" aria-label="Morning budget">
          {morningPlan.overbooked_minutes > 0 ? <><strong>Overbooked by {morningPlan.overbooked_minutes} minutes</strong><p>Your activities exceed the time before work. Free up at least {morningPlan.overbooked_minutes} minutes before adding programming.</p></> : <><strong>{availableMinutes} minutes for programming</strong><p>{availableMinutes === 0 ? 'Your routine, gym, and buffer fill the whole window. Adjust them to make room for programming.' : 'After your routine, gym, and before-work buffer.'}</p></>}
        </section>}
        {morningPlan && morningPlan.overbooked_minutes === 0 && (
          Array.isArray(morningPlan.schedule) && morningPlan.schedule.length > 0
            ? <MorningSchedule blocks={morningPlan.schedule} />
            : <p className="schedule-unavailable">No schedule was returned. Check the backend response and refresh the plan.</p>
        )}
        {activeSession && <Card className="session-card" role="region" aria-label="Active focus session">
          <div className="session-live"><span className="session-pulse" aria-hidden="true" /><div><p className="eyebrow">FOCUS SESSION IN PROGRESS</p><h2>{activeTask?.title ?? activeSession.task_id}</h2><p>Keep this page open or come back later—the session is saved.</p></div></div>
          <div className="session-clock"><Timer aria-hidden="true" /><strong aria-label={'Elapsed time ' + formatElapsed(elapsedSeconds)}>{formatElapsed(elapsedSeconds)}</strong><span>elapsed</span></div>
          {!showFinish ? <Button onClick={openFinishSession} disabled={sessionSaving}><Square aria-hidden="true" /> Finish session</Button> : <div className="finish-session">
            <div><Label htmlFor="focused-minutes">Focused minutes</Label><Input id="focused-minutes" type="number" min="1" step="1" required value={finishMinutes} disabled={sessionSaving} onChange={event => setFinishMinutes(event.target.value)} /><p>Adjust this if the timer includes a break or distraction.</p></div>
            <div className="finish-actions"><Button onClick={() => void finishSession()} disabled={sessionSaving}>{sessionSaving ? 'Saving...' : 'Save session'}</Button><Button variant="ghost" onClick={() => setShowFinish(false)} disabled={sessionSaving}>Keep working</Button></div>
          </div>}
        </Card>}
        <ActivityHeatmap refreshKey={activityVersion} />
        {selected && <Button variant="ghost" size="sm" className="refresh back-to-recommendation" disabled={noteLocked} onClick={() => setSelected(null)}>Back to morning recommendation</Button>}
        <div className="workspace"><Card className="focus" role="region" aria-label="Selected task"><p className="eyebrow">{selected ? 'TASK DETAILS' : 'YOUR NEXT STEP'}</p>{focus ? <>
          <div className="task-meta"><Badge variant="secondary" className="pill">{focus.status === 'completed' ? 'Completed' : focus.ready ? 'Ready when you are' : 'Waiting on prerequisites'}</Badge><span>{focus.estimated_minutes} min estimate</span></div>
          <h2>{focus.title}</h2><p className="deliverable">{focus.deliverable}</p>
          <TaskNote key={focus.id} taskId={focus.id} disabled={loading || saving || savingPreferences || sessionSaving} onLockChange={setNoteLocked} />
          <div className="instruction"><span className="step-number">01</span><div><h3>Start here</h3><p>{focus.first_action}</p></div></div>
          <div className="instruction"><span className="step-number">02</span><div><h3>You’re done when</h3><p>{focus.completion_check}</p></div></div>
          {!focus.ready && focus.status !== 'completed' && <p className="blocked">Finish first: {focus.prerequisites.filter(id => tasks.find(t => t.id === id)?.status !== 'completed').map(id => tasks.find(t => t.id === id)?.title ?? id).join(', ')}</p>}
          {focus.status !== 'completed' && <div className="session-start"><Button onClick={() => void startSession(focus)} disabled={busy || !focus.ready || Boolean(activeSession)}><Play aria-hidden="true" />{activeSession ? activeSession.task_id === focus.id ? 'Session in progress' : 'Another session is active' : sessionSaving ? 'Starting...' : 'Start focus session'}</Button><p>Start the timer, put your phone away, and work from the first action above.</p></div>}
          <div className="actions">{focus.status !== 'completed' ? <><Button className="primary" disabled={busy || !focus.ready} onClick={() => void update(focus, 'completed')}>{saving ? 'Saving…' : 'Mark completed'} <ArrowUpRight aria-hidden="true" /></Button>{focus.status === 'pending' && <Button variant="outline" className="secondary" disabled={busy || !focus.ready} onClick={() => void update(focus, 'in_progress')}>Set in progress</Button>}</> : <Button variant="outline" className="secondary" disabled={busy} onClick={() => void update(focus, 'pending')}>Reopen task</Button>}</div>
          <p className="footnote">Progress is saved on this laptop.</p>
        </> : <div className="empty"><h2>{loading ? 'Finding your next step…' : !recommendationLoaded ? 'Recommendation unavailable' : morningPlan && morningPlan.overbooked_minutes > 0 ? 'Make room before adding a task.' : availableMinutes === 0 ? 'No programming time left.' : tasks.length && done === tasks.length ? 'A good place to pause.' : ready.length ? 'No task fits this session.' : 'No ready tasks yet.'}</h2><p>{loading ? 'Checking your available time and prerequisites.' : !recommendationLoaded ? 'Try again to get a recommendation from your plan.' : morningPlan && morningPlan.overbooked_minutes > 0 ? 'Adjust your start times or reserved activities, then plan your morning again.' : availableMinutes === 0 ? 'Shorten an activity or extend your morning window to fit a programming session.' : tasks.length && done === tasks.length ? 'Every task in this plan is complete. Review your work or add the next task to your project plan.' : ready.length ? 'No ready task fits within ' + availableMinutes + ' minutes. Try a longer session or review your tasks.' : 'Check the tasks and their prerequisites in your project plan.'}</p></div>}</Card>
        <aside><div className="list-heading"><h2>The build, step by step</h2><Button variant="ghost" size="sm" className="refresh" onClick={() => void refresh()} disabled={busy}>{loading ? 'Loading…' : 'Refresh'}</Button></div><p className="list-caption">Each piece builds on the last.</p><div className="task-list">{tasks.map((task, index) => <Button variant="ghost" disabled={noteLocked} key={task.id} className={'task-row ' + (focus?.id === task.id ? 'selected' : '')} onClick={() => setSelected(task.id)} aria-pressed={focus?.id === task.id}><span className={'task-index ' + (task.status === 'completed' ? 'done' : '')}>{task.status === 'completed' ? <Check aria-hidden={true} /> : String(index + 1).padStart(2, '0')}</span><span><strong>{task.title}</strong><small>{task.status === 'completed' ? 'Completed' : task.ready ? task.status === 'in_progress' ? 'In progress' : 'Ready' : 'Blocked'}<span> · </span>{task.estimated_minutes} min</small></span><ArrowUpRight aria-hidden="true" /></Button>)}</div><div className="note"><Sparkles aria-hidden="true" /><p>You don’t need to finish the whole project today.<br /><strong>Just take the next clear step.</strong></p></div></aside></div>
      </>}
    </main><footer><span>MORNING PLAN / A WORK IN PROGRESS</span><span>Built by you, for your day.</span></footer>
  </div>;
}

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>);
