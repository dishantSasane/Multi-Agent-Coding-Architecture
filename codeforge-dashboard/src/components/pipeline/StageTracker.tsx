import { Check, Circle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { STAGES } from '@/lib/constants';

interface StageTrackerProps {
  currentStage: string;
}

// FAILED is an outcome, not a step in the sequence
const STEPS = STAGES.filter((s) => s.id !== 'FAILED');

/**
 * One-line summary + progress bar, with the full step list behind a disclosure.
 * Vertical, so it never scrolls sideways on a phone.
 */
export function StageTracker({ currentStage }: StageTrackerProps) {
  const failed = currentStage === 'FAILED';
  const index = STEPS.findIndex((s) => s.id === currentStage);
  const done = currentStage === 'COMPLETED';
  const label = failed ? 'Failed' : STEPS[index]?.label ?? 'Pending';
  const step = failed ? null : index + 1;

  return (
    <div>
      <div className="flex items-baseline justify-between gap-4" aria-live="polite">
        <p className="text-base font-medium">{label}</p>
        {step !== null && (
          <p className="text-xs text-muted-foreground">
            Step {step} of {STEPS.length}
          </p>
        )}
      </div>

      <div
        role="progressbar"
        aria-label="Pipeline progress"
        aria-valuemin={0}
        aria-valuemax={STEPS.length}
        aria-valuenow={failed ? 0 : step ?? 0}
        className="mt-2 h-2 overflow-hidden rounded-full bg-secondary"
      >
        <div
          className={cn(
            'h-full rounded-full transition-[width] duration-200 ease-out',
            failed ? 'w-full bg-destructive' : 'bg-primary'
          )}
          style={failed ? undefined : { width: `${((step ?? 0) / STEPS.length) * 100}%` }}
        />
      </div>

      <details className="mt-4 text-sm">
        <summary className="cursor-pointer rounded-lg py-2 text-muted-foreground transition-colors duration-150 ease-out hover:text-foreground">
          All steps
        </summary>
        <ol className="mt-2 space-y-2">
          {STEPS.map((s, i) => {
            const isDone = done || (!failed && i < index);
            const isCurrent = !failed && !done && i === index;
            return (
              <li
                key={s.id}
                aria-current={isCurrent ? 'step' : undefined}
                className={cn(
                  'flex items-center gap-2',
                  isCurrent ? 'font-medium text-foreground' : isDone ? 'text-foreground' : 'text-muted-foreground'
                )}
              >
                {isDone ? (
                  <Check className="h-4 w-4 text-success" aria-hidden="true" />
                ) : (
                  <Circle className="h-4 w-4" aria-hidden="true" />
                )}
                <span>{s.label}</span>
                <span className="sr-only">{isDone ? '(done)' : isCurrent ? '(current)' : '(pending)'}</span>
              </li>
            );
          })}
        </ol>
      </details>
    </div>
  );
}
