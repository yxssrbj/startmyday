import { useEffect, useMemo, useRef, useState } from 'react';
import { CalendarDays, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

type ActivityDay = { date: string; minutes: number };
type HeatmapDay = { date: string; label: string; minutes: number; future: boolean };

function dateKey(date: Date) {
  return [date.getFullYear(), String(date.getMonth() + 1).padStart(2, '0'), String(date.getDate()).padStart(2, '0')].join('-');
}

function activityLevel(minutes: number) {
  if (minutes >= 120) return 4;
  if (minutes >= 60) return 3;
  if (minutes >= 30) return 2;
  if (minutes > 0) return 1;
  return 0;
}

function formatMinutes(minutes: number) {
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return remainder ? `${hours}h ${remainder}m` : `${hours}h`;
}

export function ActivityHeatmap({ refreshKey }: { refreshKey: number }) {
  const range = useMemo(() => {
    const today = new Date();
    today.setHours(12, 0, 0, 0);
    const mondayOffset = (today.getDay() + 6) % 7;
    const start = new Date(today);
    start.setDate(today.getDate() - mondayOffset - 11 * 7);
    const end = new Date(start);
    end.setDate(start.getDate() + 83);
    return { today, start, end };
  }, []);
  const [activity, setActivity] = useState<ActivityDay[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retryKey, setRetryKey] = useState(0);
  const gridScrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function loadActivity() {
      setLoading(true); setError('');
      try {
        const response = await fetch(`/api/activity?start=${dateKey(range.start)}&end=${dateKey(range.today)}`, { signal: controller.signal });
        const data = await response.json().catch(() => null);
        if (!response.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : 'Could not load activity.');
        setActivity(Array.isArray(data) ? data : []);
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') return;
        setError(error instanceof Error ? error.message : 'Could not load activity.');
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void loadActivity();
    return () => controller.abort();
  }, [range, refreshKey, retryKey]);

  const minutesByDate = new Map(activity.map(day => [day.date, day.minutes]));
  const days: HeatmapDay[] = [];
  for (let index = 0; index < 84; index++) {
    const date = new Date(range.start);
    date.setDate(range.start.getDate() + index);
    const key = dateKey(date);
    days.push({
      date: key,
      label: date.toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' }),
      minutes: minutesByDate.get(key) ?? 0,
      future: date > range.today,
    });
  }
  const totalMinutes = activity.reduce((sum, day) => sum + day.minutes, 0);
  const activeDays = activity.filter(day => day.minutes > 0).length;

  useEffect(() => {
    const scroller = gridScrollRef.current;
    if (scroller) scroller.scrollLeft = scroller.scrollWidth;
  }, [activity]);

  return <Card className="activity-card" aria-labelledby="activity-title">
    <div className="activity-heading">
      <div className="activity-title"><span className="activity-icon"><CalendarDays aria-hidden="true" /></span><div><p className="eyebrow">CONSISTENCY</p><h2 id="activity-title">Your programming activity</h2><p>Focused minutes from completed sessions over the last 12 weeks.</p></div></div>
      <div className="activity-stats" aria-label={`${formatMinutes(totalMinutes)} focused across ${activeDays} active days`}><strong>{formatMinutes(totalMinutes)}</strong><span>{activeDays} active {activeDays === 1 ? 'day' : 'days'}</span></div>
    </div>
    {error ? <div className="activity-error" role="alert"><span>{error}</span><Button variant="outline" size="sm" onClick={() => setRetryKey(key => key + 1)}><RefreshCw aria-hidden="true" /> Try again</Button></div> : <>
      <div className="heatmap-scroll" aria-busy={loading}>
        <div className="heatmap-weekdays" aria-hidden="true"><span>Mon</span><span>Wed</span><span>Fri</span></div>
        <div className="heatmap-grid-scroll" ref={gridScrollRef}>
          <div className="heatmap-grid" role="img" aria-label={`Programming activity for the last 12 weeks. ${formatMinutes(totalMinutes)} across ${activeDays} active days.`}>
            {days.map(day => <span key={day.date} className={`heatmap-cell level-${activityLevel(day.minutes)}${day.future ? ' future' : ''}`} title={day.future ? day.label : `${day.label}: ${day.minutes ? formatMinutes(day.minutes) : 'No focused time'}`} aria-hidden="true" />)}
          </div>
        </div>
      </div>
      <div className="heatmap-footer"><span>{loading ? 'Loading activity…' : `${range.start.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })} – ${range.today.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`}</span><div className="heatmap-legend" aria-hidden="true"><span>Less</span>{[0, 1, 2, 3, 4].map(level => <i key={level} className={`heatmap-cell level-${level}`} />)}<span>More</span></div></div>
    </>}
  </Card>;
}
