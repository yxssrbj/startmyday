import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Coffee, Code2, Dumbbell, Clock3 } from 'lucide-react';

export type ScheduleBlock = {
  activity: string;
  start: string;
  end: string;
};

const activities = {
  routine: { label: 'Morning routine', Icon: Coffee },
  programming: { label: 'Programming', Icon: Code2 },
  gym: { label: 'Gym', Icon: Dumbbell },
  buffer: { label: 'Before-work buffer', Icon: Clock3 },
};

// The form sends same-day local timestamps. Preserve the API's wall-clock times.
function clockTime(timestamp: string) {
  return timestamp.split('T')[1]?.slice(0, 5) ?? timestamp;
}

export function MorningSchedule({ blocks }: { blocks: ScheduleBlock[] }) {
  return <Card className="schedule-card" role="region" aria-labelledby="schedule-heading">
    <div className="schedule-heading">
      <div><h2 id="schedule-heading">Your morning, in order</h2><p>Local times · Programming is the full available window.</p></div>
      <Badge variant="outline">{blocks.length} {blocks.length === 1 ? 'activity' : 'activities'}</Badge>
    </div>
    <ol className="schedule-blocks">
      {blocks.map((block, index) => {
        const { label, Icon } = activities[block.activity as keyof typeof activities] ?? { label: block.activity, Icon: Clock3 };
        const duration = (new Date(block.end).getTime() - new Date(block.start).getTime()) / 60000;
        return <li key={block.activity + block.start + index} className={'schedule-block ' + (block.activity === 'programming' ? 'programming-block' : '')}>
          <div className="schedule-block-top"><Icon aria-hidden="true" /><span>{Number.isFinite(duration) ? Math.round(duration * 100) / 100 + ' min' : ''}</span></div>
          <h3>{label}</h3>
          <p><time dateTime={block.start}>{clockTime(block.start)}</time><span aria-hidden="true"> – </span><span className="sr-only"> to </span><time dateTime={block.end}>{clockTime(block.end)}</time></p>
        </li>;
      })}
    </ol>
  </Card>;
}
