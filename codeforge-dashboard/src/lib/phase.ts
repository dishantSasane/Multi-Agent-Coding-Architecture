import type { Task } from '@/types';

/** One explicit UI state, derived from the server status, instead of chained booleans. */
export type Phase =
  | 'idle'
  | 'submitting'
  | 'analysing'
  | 'awaiting_confirmation'
  | 'generating'
  | 'validating'
  | 'done'
  | 'failed';

export function phaseOf(status: Task['status'] | undefined, submitting: boolean): Phase {
  if (submitting) return 'submitting';
  switch (status) {
    case undefined:
      return 'idle';
    case 'PENDING':
    case 'INTENT_ANALYZING':
      return 'analysing';
    case 'AWAITING_CONFIRMATION':
      return 'awaiting_confirmation';
    case 'CONFIRMED':
    case 'DECOMPOSING':
    case 'GENERATING':
    case 'DEBATING':
    case 'SYNTHESIZING':
      return 'generating';
    case 'VALIDATING':
    case 'SANDBOX_EXECUTING':
    case 'CORRECTING':
      return 'validating';
    case 'COMPLETED':
      return 'done';
    case 'FAILED':
      return 'failed';
  }
}

/** The backend is working (not waiting on the user, not finished). */
export const isBusy = (p: Phase): boolean =>
  p === 'submitting' || p === 'analysing' || p === 'generating' || p === 'validating';
