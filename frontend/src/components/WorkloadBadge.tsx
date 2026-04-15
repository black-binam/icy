import { cn } from '@/lib/utils';
import { formatMinutes } from '@/lib/utils';

interface WorkloadBadgeProps {
  minutes: number;
  capacityMinutes: number;
  label?: string;
  className?: string;
}

/**
 * Affiche la charge d'un soignant sous forme de barre + pourcentage,
 * teintée selon l'équité : vert (sous-utilisé), ambre (bon), rouge (surcharge).
 */
export function WorkloadBadge({ minutes, capacityMinutes, label, className }: WorkloadBadgeProps) {
  const safeCapacity = Math.max(1, capacityMinutes);
  const ratio = minutes / safeCapacity;
  const pct = Math.min(120, Math.round(ratio * 100));

  let tone: 'under' | 'ok' | 'over' = 'ok';
  if (ratio < 0.6) tone = 'under';
  else if (ratio > 1) tone = 'over';

  const toneStyles = {
    under: {
      bar: 'bg-primary-400',
      text: 'text-primary-700',
      track: 'bg-primary/10',
    },
    ok: {
      bar: 'bg-success',
      text: 'text-success',
      track: 'bg-success/10',
    },
    over: {
      bar: 'bg-destructive',
      text: 'text-destructive',
      track: 'bg-destructive/10',
    },
  } as const;

  const styles = toneStyles[tone];

  return (
    <div className={cn('flex w-full flex-col gap-1', className)}>
      <div className="flex items-center justify-between gap-4 text-sm">
        {label ? <span className="font-medium text-foreground">{label}</span> : <span />}
        <span className={cn('font-mono text-xs', styles.text)}>
          {formatMinutes(minutes)} / {formatMinutes(capacityMinutes)} · {pct}%
        </span>
      </div>
      <div
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        className={cn('h-2 w-full overflow-hidden rounded-full', styles.track)}
      >
        <div
          className={cn('h-full rounded-full transition-all', styles.bar)}
          style={{ width: `${Math.min(100, pct)}%` }}
        />
      </div>
    </div>
  );
}
