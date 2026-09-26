import { useEffect, useState } from 'react';
import { ArrowDown, ArrowUp, Check, FolderKanban, Pencil, Plus, Trash2, X } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

type ProjectSummary = {
  project_id: string; name: string; goal: string; is_active: boolean;
  task_count: number; created_at: string; updated_at: string;
};
type ProjectTask = {
  id: string; title: string; deliverable: string; first_action: string;
  completion_check: string; estimated_minutes: number; prerequisites: string[];
};
type ProjectDetail = {
  project_id: string; name: string; goal: string; tasks: ProjectTask[];
};
type TaskDraft = {
  title: string; deliverable: string; first_action: string;
  completion_check: string; estimated_minutes: string; prerequisites: string[];
};

const emptyTask = (): TaskDraft => ({
  title: '', deliverable: '', first_action: '', completion_check: '',
  estimated_minutes: '30', prerequisites: [],
});

async function apiRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, options);
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data?.detail;
    throw new Error(typeof detail === 'string' ? detail : Array.isArray(detail)
      ? detail.map(item => item?.msg ?? String(item)).join(' · ')
      : 'The request could not be completed.');
  }
  return data;
}

export function ProjectWorkspace({ onActiveProjectChange }: { onActiveProjectChange: () => void }) {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [creatingProject, setCreatingProject] = useState(false);
  const [newProject, setNewProject] = useState({ name: '', goal: '' });
  const [projectDraft, setProjectDraft] = useState({ name: '', goal: '' });
  const [editingTaskId, setEditingTaskId] = useState<string | null>(null);
  const [taskDraft, setTaskDraft] = useState<TaskDraft>(emptyTask);

  async function loadProject(projectId: string) {
    const detail = await apiRequest<ProjectDetail>('/api/projects/' + encodeURIComponent(projectId));
    setProject(detail);
    setProjectDraft({ name: detail.name, goal: detail.goal });
  }

  async function loadProjects(preferredId?: string | null) {
    setLoading(true); setError('');
    try {
      const list = await apiRequest<ProjectSummary[]>('/api/projects');
      setProjects(list);
      const nextId = preferredId && list.some(item => item.project_id === preferredId)
        ? preferredId
        : list.find(item => item.is_active)?.project_id ?? list[0]?.project_id ?? null;
      setSelectedId(nextId);
      if (nextId) await loadProject(nextId);
      else setProject(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load projects.');
    } finally { setLoading(false); }
  }

  useEffect(() => { void loadProjects(); }, []);

  async function selectProject(projectId: string) {
    if (saving) return;
    setSelectedId(projectId); setEditingTaskId(null); setError(''); setNotice('');
    try { await loadProject(projectId); }
    catch (caught) { setError(caught instanceof Error ? caught.message : 'Could not load the project.'); }
  }

  async function createNewProject() {
    if (!newProject.name.trim() || saving) return;
    setSaving(true); setError(''); setNotice('');
    try {
      const created = await apiRequest<ProjectDetail>('/api/projects', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newProject),
      });
      setNewProject({ name: '', goal: '' }); setCreatingProject(false);
      await loadProjects(created.project_id);
      setNotice('Project created. Add its first concrete task.');
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'Could not create the project.'); }
    finally { setSaving(false); }
  }

  async function saveProjectDetails() {
    if (!project || !projectDraft.name.trim() || saving) return;
    setSaving(true); setError(''); setNotice('');
    try {
      await apiRequest('/api/projects/' + encodeURIComponent(project.project_id), {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(projectDraft),
      });
      await loadProjects(project.project_id);
      setNotice('Project details saved.');
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'Could not save the project.'); }
    finally { setSaving(false); }
  }

  async function activateSelectedProject() {
    if (!project || saving) return;
    setSaving(true); setError(''); setNotice('');
    try {
      await apiRequest('/api/projects/' + encodeURIComponent(project.project_id) + '/active', { method: 'PUT' });
      await loadProjects(project.project_id);
      onActiveProjectChange();
      setNotice('This project now drives Today.');
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'Could not activate the project.'); }
    finally { setSaving(false); }
  }

  async function removeSelectedProject() {
    if (!project || saving || !window.confirm(`Delete “${project.name}” and all of its local task data?`)) return;
    setSaving(true); setError(''); setNotice('');
    try {
      const result = await apiRequest<{ active_project_id: string | null }>(
        '/api/projects/' + encodeURIComponent(project.project_id), { method: 'DELETE' },
      );
      setEditingTaskId(null);
      await loadProjects(result.active_project_id);
      onActiveProjectChange();
      setNotice('Project deleted.');
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'Could not delete the project.'); }
    finally { setSaving(false); }
  }

  function openNewTask() {
    setEditingTaskId('new'); setTaskDraft(emptyTask()); setError(''); setNotice('');
  }

  function openTask(task: ProjectTask) {
    setEditingTaskId(task.id);
    setTaskDraft({
      title: task.title, deliverable: task.deliverable, first_action: task.first_action,
      completion_check: task.completion_check,
      estimated_minutes: String(task.estimated_minutes), prerequisites: [...task.prerequisites],
    });
    setError(''); setNotice('');
  }

  async function saveTask() {
    if (!project || !editingTaskId || saving) return;
    const minutes = Number(taskDraft.estimated_minutes);
    if (!taskDraft.title.trim() || !taskDraft.deliverable.trim() || !taskDraft.first_action.trim()
      || !taskDraft.completion_check.trim() || !Number.isSafeInteger(minutes) || minutes <= 0) {
      setError('Complete every task field and use a positive whole-number estimate.');
      return;
    }
    const affectsToday = Boolean(selectedSummary?.is_active);
    setSaving(true); setError(''); setNotice('');
    try {
      const body = {
        ...taskDraft, estimated_minutes: minutes,
        title: taskDraft.title.trim(), deliverable: taskDraft.deliverable.trim(),
        first_action: taskDraft.first_action.trim(), completion_check: taskDraft.completion_check.trim(),
      };
      if (editingTaskId === 'new') {
        await apiRequest('/api/projects/' + encodeURIComponent(project.project_id) + '/tasks', {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
        });
      } else {
        await apiRequest('/api/tasks/' + encodeURIComponent(editingTaskId), {
          method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
        });
      }
      setEditingTaskId(null); setTaskDraft(emptyTask());
      await loadProjects(project.project_id);
      if (affectsToday) onActiveProjectChange();
      setNotice(editingTaskId === 'new' ? 'Task added.' : 'Task updated.');
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'Could not save the task.'); }
    finally { setSaving(false); }
  }

  async function removeTask(task: ProjectTask) {
    if (!project || saving || !window.confirm(`Delete “${task.title}” and its local history?`)) return;
    const affectsToday = Boolean(selectedSummary?.is_active);
    setSaving(true); setError(''); setNotice('');
    try {
      await apiRequest('/api/tasks/' + encodeURIComponent(task.id), { method: 'DELETE' });
      if (editingTaskId === task.id) setEditingTaskId(null);
      await loadProjects(project.project_id);
      if (affectsToday) onActiveProjectChange();
      setNotice('Task deleted.');
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'Could not delete the task.'); }
    finally { setSaving(false); }
  }

  async function moveTask(index: number, direction: -1 | 1) {
    if (!project || saving) return;
    const target = index + direction;
    if (target < 0 || target >= project.tasks.length) return;
    const ordered = project.tasks.map(task => task.id);
    [ordered[index], ordered[target]] = [ordered[target], ordered[index]];
    const affectsToday = Boolean(selectedSummary?.is_active);
    setSaving(true); setError(''); setNotice('');
    try {
      await apiRequest('/api/projects/' + encodeURIComponent(project.project_id) + '/tasks/order', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_ids: ordered }),
      });
      await loadProject(project.project_id);
      if (affectsToday) onActiveProjectChange();
      setNotice('Task order updated.');
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'Could not reorder tasks.'); }
    finally { setSaving(false); }
  }

  const selectedSummary = projects.find(item => item.project_id === selectedId);
  const formCandidates = project?.tasks.filter(task => task.id !== editingTaskId) ?? [];

  return <section className="projects-only project-workspace" aria-label="Project workspace">
    <div className="projects-heading"><div><p className="eyebrow">PROJECT WORKSPACE</p><h2>Choose what Today should move forward.</h2><p>Create concrete tasks here, then activate the project you want the morning planner to use.</p></div><Button onClick={() => setCreatingProject(true)} disabled={saving}><Plus aria-hidden="true" />New project</Button></div>
    {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
    {notice && <p className="project-notice" role="status">{notice}</p>}
    {creatingProject && <Card className="project-create-card"><div><Label htmlFor="new-project-name">Project name</Label><Input id="new-project-name" value={newProject.name} onChange={event => setNewProject(current => ({ ...current, name: event.target.value }))} placeholder="Build a personal finance API" /></div><div><Label htmlFor="new-project-goal">Goal</Label><Textarea id="new-project-goal" value={newProject.goal} onChange={event => setNewProject(current => ({ ...current, goal: event.target.value }))} placeholder="What should this project help you learn or accomplish?" /></div><div className="project-form-actions"><Button variant="ghost" onClick={() => setCreatingProject(false)}><X aria-hidden="true" />Cancel</Button><Button disabled={saving || !newProject.name.trim()} onClick={() => void createNewProject()}>{saving ? 'Creating...' : 'Create project'}</Button></div></Card>}
    <div className="projects-layout">
      <aside className="project-library"><div className="project-library-title"><FolderKanban aria-hidden="true" /><div><strong>Your projects</strong><span>{projects.length} total</span></div></div>{loading ? <p>Loading projects…</p> : projects.length === 0 ? <div className="project-empty"><p>No projects yet.</p><Button size="sm" onClick={() => setCreatingProject(true)}>Create the first one</Button></div> : <div className="project-picker">{projects.map(item => <button type="button" key={item.project_id} className={item.project_id === selectedId ? 'selected' : ''} onClick={() => void selectProject(item.project_id)}><span><strong>{item.name}</strong><small>{item.task_count} {item.task_count === 1 ? 'task' : 'tasks'}</small></span>{item.is_active && <Badge>Active</Badge>}</button>)}</div>}</aside>
      <div className="project-editor">{project ? <>
        <Card className="project-details"><div className="project-details-heading"><div><p className="eyebrow">PROJECT DETAILS</p><h3>{project.name}</h3></div><div className="project-header-actions">{!selectedSummary?.is_active && <Button variant="outline" onClick={() => void activateSelectedProject()} disabled={saving}><Check aria-hidden="true" />Use on Today</Button>}<Button variant="ghost" className="danger-action" onClick={() => void removeSelectedProject()} disabled={saving}><Trash2 aria-hidden="true" />Delete</Button></div></div><div className="project-detail-fields"><div><Label htmlFor="project-name">Name</Label><Input id="project-name" value={projectDraft.name} onChange={event => setProjectDraft(current => ({ ...current, name: event.target.value }))} /></div><div><Label htmlFor="project-goal">Goal</Label><Textarea id="project-goal" value={projectDraft.goal} onChange={event => setProjectDraft(current => ({ ...current, goal: event.target.value }))} placeholder="Describe the outcome you are working toward." /></div></div><Button variant="outline" disabled={saving || !projectDraft.name.trim()} onClick={() => void saveProjectDetails()}>{saving ? 'Saving...' : 'Save project details'}</Button></Card>
        <div className="project-tasks-heading"><div><p className="eyebrow">SEQUENCED DELIVERABLES</p><h3>Tasks build on the work before them.</h3></div><Button onClick={openNewTask} disabled={saving}><Plus aria-hidden="true" />Add task</Button></div>
        {editingTaskId && <Card className="task-editor-card"><div className="task-editor-heading"><h3>{editingTaskId === 'new' ? 'Add a concrete task' : 'Edit task'}</h3><Button variant="ghost" size="sm" onClick={() => setEditingTaskId(null)}><X aria-hidden="true" />Close</Button></div><div className="task-editor-grid"><div><Label htmlFor="task-title">Title</Label><Input id="task-title" value={taskDraft.title} onChange={event => setTaskDraft(current => ({ ...current, title: event.target.value }))} /></div><div><Label htmlFor="task-minutes">Estimate (minutes)</Label><Input id="task-minutes" type="number" min="1" step="1" value={taskDraft.estimated_minutes} onChange={event => setTaskDraft(current => ({ ...current, estimated_minutes: event.target.value }))} /></div><div className="task-field-wide"><Label htmlFor="task-deliverable">Concrete deliverable</Label><Textarea id="task-deliverable" value={taskDraft.deliverable} onChange={event => setTaskDraft(current => ({ ...current, deliverable: event.target.value }))} /></div><div><Label htmlFor="task-action">First action</Label><Textarea id="task-action" value={taskDraft.first_action} onChange={event => setTaskDraft(current => ({ ...current, first_action: event.target.value }))} /></div><div><Label htmlFor="task-check">Completion check</Label><Textarea id="task-check" value={taskDraft.completion_check} onChange={event => setTaskDraft(current => ({ ...current, completion_check: event.target.value }))} /></div></div><fieldset className="prerequisite-picker"><legend>Prerequisites</legend>{formCandidates.length ? formCandidates.map(candidate => <label key={candidate.id}><input type="checkbox" checked={taskDraft.prerequisites.includes(candidate.id)} onChange={event => setTaskDraft(current => ({ ...current, prerequisites: event.target.checked ? [...current.prerequisites, candidate.id] : current.prerequisites.filter(id => id !== candidate.id) }))} /><span>{candidate.title}</span></label>) : <p>No other tasks can be prerequisites yet.</p>}</fieldset><div className="task-editor-actions"><Button variant="ghost" onClick={() => setEditingTaskId(null)}>Cancel</Button><Button disabled={saving} onClick={() => void saveTask()}>{saving ? 'Saving...' : editingTaskId === 'new' ? 'Add task' : 'Save task'}</Button></div></Card>}
        <div className="project-task-list">{project.tasks.length === 0 ? <Card className="project-empty-state"><p className="eyebrow">START THE PLAN</p><h3>Add the first deliverable.</h3><p>Give it a concrete result, a first action, and a check that proves it works.</p><Button onClick={openNewTask}><Plus aria-hidden="true" />Add first task</Button></Card> : project.tasks.map((task, index) => <Card key={task.id} className="project-task-row"><span className="project-task-number">{String(index + 1).padStart(2, '0')}</span><div className="project-task-copy"><div><h4>{task.title}</h4><span>{task.estimated_minutes} min</span></div><p>{task.deliverable}</p>{task.prerequisites.length > 0 && <small>After: {task.prerequisites.map(id => project.tasks.find(item => item.id === id)?.title ?? id).join(', ')}</small>}</div><div className="project-task-actions"><Button variant="ghost" size="icon" aria-label={'Move ' + task.title + ' up'} disabled={saving || index === 0} onClick={() => void moveTask(index, -1)}><ArrowUp aria-hidden="true" /></Button><Button variant="ghost" size="icon" aria-label={'Move ' + task.title + ' down'} disabled={saving || index === project.tasks.length - 1} onClick={() => void moveTask(index, 1)}><ArrowDown aria-hidden="true" /></Button><Button variant="ghost" size="icon" aria-label={'Edit ' + task.title} disabled={saving} onClick={() => openTask(task)}><Pencil aria-hidden="true" /></Button><Button variant="ghost" size="icon" className="danger-action" aria-label={'Delete ' + task.title} disabled={saving} onClick={() => void removeTask(task)}><Trash2 aria-hidden="true" /></Button></div></Card>)}</div>
      </> : <Card className="project-empty-state"><h3>Select or create a project.</h3><p>Your active project will supply the tasks shown on Today.</p></Card>}</div>
    </div>
  </section>;
}
