export const STAGES = [
  { id: 'PENDING', label: 'Pending' },
  { id: 'INTENT_ANALYZING', label: 'Analyzing Intent' },
  { id: 'AWAITING_CONFIRMATION', label: 'Awaiting Confirmation' },
  { id: 'CONFIRMED', label: 'Confirmed' },
  { id: 'DECOMPOSING', label: 'Decomposing' },
  { id: 'GENERATING', label: 'Generating' },
  { id: 'DEBATING', label: 'Debating' },
  { id: 'SYNTHESIZING', label: 'Synthesizing' },
  { id: 'VALIDATING', label: 'Validating' },
  { id: 'SANDBOX_EXECUTING', label: 'Executing' },
  { id: 'CORRECTING', label: 'Self-Correcting' },
  { id: 'COMPLETED', label: 'Completed' },
  { id: 'FAILED', label: 'Failed' },
];

export const MAX_QUERY_LENGTH = 2000;
