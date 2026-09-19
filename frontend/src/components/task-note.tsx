import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';

type SavedNote = { note: string; updated_at: string | null };

async function noteRequest(taskId: string, options?: RequestInit): Promise<SavedNote> {
  const response = await fetch('/api/tasks/' + encodeURIComponent(taskId) + '/note', options);
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : 'Could not reach your notes. Please try again.');
  return data;
}

function updatedLabel(timestamp: string) {
  // SQLite CURRENT_TIMESTAMP is UTC even though its string has no offset.
  const iso = timestamp.replace(' ', 'T');
  const date = new Date(/[zZ]|[+-]\d\d:\d\d$/.test(iso) ? iso : iso + 'Z');
  return Number.isNaN(date.getTime()) ? timestamp : date.toLocaleString();
}

export function TaskNote({ taskId, disabled, onLockChange }: {
  taskId: string; disabled: boolean; onLockChange: (locked: boolean) => void;
}) {
  const [saved, setSaved] = useState<SavedNote | null>(null);
  const [draft, setDraft] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [retry, setRetry] = useState(0);
  const dirty = saved !== null && draft !== saved.note;

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError('');
    noteRequest(taskId, { signal: controller.signal }).then(note => {
      if (controller.signal.aborted) return;
      setSaved(note); setDraft(note.note);
    }).catch(error => {
      if (!controller.signal.aborted) setError(error instanceof Error ? error.message : 'Could not load your note.');
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [taskId, retry]);

  useEffect(() => {
    onLockChange(dirty || saving);
    return () => onLockChange(false);
  }, [dirty, saving, onLockChange]);

  useEffect(() => {
    if (!dirty && !saving) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ''; };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [dirty, saving]);

  async function save(note: string) {
    setSaving(true); setError(''); setMessage('');
    try {
      const result = await noteRequest(taskId, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ note }),
      });
      setSaved(result); setDraft(result.note);
      setMessage(result.note ? 'Note saved.' : 'Note cleared.');
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Could not save your note.');
    } finally { setSaving(false); }
  }

  return <section className="task-note" aria-label="Continue here tomorrow">
    <Label htmlFor={'task-note-' + taskId}>Continue here tomorrow</Label>
    <p className="task-note-hint">Leave your next action, where to find it, and anything you got stuck on.</p>
    {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription>
      {!saved && <Button variant="outline" size="sm" onClick={() => setRetry(value => value + 1)} disabled={loading}>Retry loading note</Button>}
    </Alert>}
    {loading ? <p role="status">Loading your note…</p> : saved && <>
      <Textarea id={'task-note-' + taskId} value={draft} rows={4}
        placeholder="Next: test the zero-duration case. Start in tests/test_morning_plan.py."
        disabled={disabled || saving} onChange={event => { setDraft(event.target.value); setMessage(''); }}
        aria-describedby={'note-help-' + taskId} />
      <div className="note-controls">
        <Button size="sm" onClick={() => void save(draft)} disabled={disabled || saving || !dirty}>{saving ? 'Saving note…' : 'Save note'}</Button>
        {dirty && <Button size="sm" variant="outline" disabled={disabled || saving} onClick={() => { setDraft(saved.note); setError(''); setMessage('Changes discarded.'); }}>Discard changes</Button>}
        <Button size="sm" variant="ghost" onClick={() => void save('')} disabled={disabled || saving || (!saved.note && !draft)}>Clear note</Button>
      </div>
      <p id={'note-help-' + taskId} className="note-save-state">{dirty ? 'Unsaved changes. Save or discard before switching tasks or updating the plan.' : saved.updated_at ? 'Last saved: ' + updatedLabel(saved.updated_at) : 'No saved note yet.'}</p>
    </>}
    <p className="note-feedback" role="status">{message}</p>
  </section>;
}
