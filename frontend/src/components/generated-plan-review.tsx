import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

export type DraftTask = {
  draft_id: string; title: string; deliverable: string; first_action: string;
  completion_check: string; estimated_minutes: number; prerequisites: string[];
};

export type GeneratedPlan = {
  name: string; goal: string; summary: string; assumptions: string[]; tasks: DraftTask[];
};

export function GeneratedPlanReview({ plan, onChange, onSave, onDiscard, saving }: {
  plan: GeneratedPlan;
  onChange: (plan: GeneratedPlan) => void;
  onSave: () => void;
  onDiscard: () => void;
  saving: boolean;
}) {
  function updateTask(index: number, changes: Partial<DraftTask>) {
    onChange({ ...plan, tasks: plan.tasks.map((task, taskIndex) =>
      taskIndex === index ? { ...task, ...changes } : task) });
  }

  function removeTask(index: number) {
    onChange({ ...plan, tasks: plan.tasks.filter((_, taskIndex) => taskIndex !== index) });
  }

  const valid = Boolean(plan.name.trim() && plan.goal.trim() && plan.tasks.length &&
    plan.tasks.every(task => task.title.trim() && task.deliverable.trim() &&
      task.first_action.trim() && task.completion_check.trim() &&
      Number.isSafeInteger(task.estimated_minutes) && task.estimated_minutes > 0));

  return <div className="generated-plan-review" role="region" aria-label="Generated project draft">
    <div className="generated-plan-heading"><div><p className="eyebrow">REVIEW BEFORE SAVING</p><h3>Make this plan yours.</h3><p>{plan.summary}</p></div><Button variant="ghost" onClick={onDiscard} disabled={saving}>Discard draft</Button></div>
    {plan.assumptions.length > 0 && <div className="generated-plan-assumptions"><strong>Assumptions to check</strong><ul>{plan.assumptions.map((item, index) => <li key={index}>{item}</li>)}</ul></div>}
    <div className="generated-plan-project-fields"><div><Label htmlFor="draft-project-name">Project name</Label><Input id="draft-project-name" value={plan.name} disabled={saving} onChange={event => onChange({ ...plan, name: event.target.value })} /></div><div><Label htmlFor="draft-project-goal">Goal</Label><Textarea id="draft-project-goal" value={plan.goal} disabled={saving} onChange={event => onChange({ ...plan, goal: event.target.value })} /></div></div>
    <div className="generated-plan-tasks">{plan.tasks.map((task, index) => {
      const hasDependents = plan.tasks.some(other => other.prerequisites.includes(task.draft_id));
      return <div className="generated-plan-task" key={task.draft_id}>
        <div className="generated-plan-task-heading"><strong>{String(index + 1).padStart(2, '0')} · Task</strong><Button variant="ghost" size="sm" disabled={saving || hasDependents || plan.tasks.length === 1} title={hasDependents ? 'Remove this task from later prerequisites first.' : undefined} onClick={() => removeTask(index)}>Remove</Button></div>
        <div className="generated-plan-task-fields">
          <div><Label htmlFor={`draft-title-${task.draft_id}`}>Title</Label><Input id={`draft-title-${task.draft_id}`} value={task.title} disabled={saving} onChange={event => updateTask(index, { title: event.target.value })} /></div>
          <div><Label htmlFor={`draft-minutes-${task.draft_id}`}>Estimate (minutes)</Label><Input id={`draft-minutes-${task.draft_id}`} type="number" min="1" step="1" value={task.estimated_minutes} disabled={saving} onChange={event => updateTask(index, { estimated_minutes: Number(event.target.value) })} /></div>
          <div className="generated-plan-wide"><Label htmlFor={`draft-deliverable-${task.draft_id}`}>Concrete deliverable</Label><Textarea id={`draft-deliverable-${task.draft_id}`} value={task.deliverable} disabled={saving} onChange={event => updateTask(index, { deliverable: event.target.value })} /></div>
          <div><Label htmlFor={`draft-action-${task.draft_id}`}>First action</Label><Textarea id={`draft-action-${task.draft_id}`} value={task.first_action} disabled={saving} onChange={event => updateTask(index, { first_action: event.target.value })} /></div>
          <div><Label htmlFor={`draft-check-${task.draft_id}`}>Completion check</Label><Textarea id={`draft-check-${task.draft_id}`} value={task.completion_check} disabled={saving} onChange={event => updateTask(index, { completion_check: event.target.value })} /></div>
        </div>
        <fieldset className="generated-plan-prerequisites"><legend>Finish first</legend>{index === 0 ? <p>No earlier tasks.</p> : plan.tasks.slice(0, index).map(candidate => <label key={candidate.draft_id}><input type="checkbox" checked={task.prerequisites.includes(candidate.draft_id)} disabled={saving} onChange={event => updateTask(index, { prerequisites: event.target.checked ? [...task.prerequisites, candidate.draft_id] : task.prerequisites.filter(id => id !== candidate.draft_id) })} /><span>{candidate.title}</span></label>)}</fieldset>
      </div>;
    })}</div>
    <div className="generated-plan-footer"><p>Saving creates a new project. It will not replace the project on Today.</p><Button onClick={onSave} disabled={saving || !valid}>{saving ? 'Saving…' : `Save project with ${plan.tasks.length} tasks`}</Button></div>
  </div>;
}
