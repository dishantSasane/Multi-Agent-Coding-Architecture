export const STAGES = [
  { id: 'PENDING', label: 'Pending', icon: '⏳' },
  { id: 'INTENT_ANALYZING', label: 'Analyzing Intent', icon: '🔍' },
  { id: 'AWAITING_CONFIRMATION', label: 'Awaiting Confirmation', icon: '❓' },
  { id: 'CONFIRMED', label: 'Confirmed', icon: '✅' },
  { id: 'DECOMPOSING', label: 'Decomposing', icon: '🔧' },
  { id: 'GENERATING', label: 'Generating', icon: '✨' },
  { id: 'DEBATING', label: 'Debating', icon: '💬' },
  { id: 'SYNTHESIZING', label: 'Synthesizing', icon: '🔗' },
  { id: 'VALIDATING', label: 'Validating', icon: '🧪' },
  { id: 'SANDBOX_EXECUTING', label: 'Executing', icon: '📦' },
  { id: 'CORRECTING', label: 'Self-Correcting', icon: '🔄' },
  { id: 'COMPLETED', label: 'Completed', icon: '🎉' },
  { id: 'FAILED', label: 'Failed', icon: '❌' },
];

export const MODELS = [
  { id: 'claude', name: 'Claude 3.5 Sonnet', provider: 'Anthropic' },
  { id: 'gpt-4o', name: 'GPT-4o', provider: 'OpenAI' },
  { id: 'qwen', name: 'Qwen2.5-Coder', provider: 'Alibaba' },
  { id: 'kimi', name: 'Kimi k1.5', provider: 'Moonshot' },
  { id: 'gemini', name: 'Gemini 1.5 Pro', provider: 'Google' },
];

export const VALIDATION_STAGES = [
  { id: 'syntax', label: 'Syntax Check' },
  { id: 'static_analysis', label: 'Static Analysis' },
  { id: 'security', label: 'Security Scan' },
  { id: 'unit_tests', label: 'Unit Tests' },
  { id: 'property_tests', label: 'Property Tests' },
];

export const MAX_QUERY_LENGTH = 2000;
export const WS_RECONNECT_INTERVALS = [1000, 2000, 4000, 8000, 30000];
export const WS_HEARTBEAT_INTERVAL = 30000;
export const POLL_INTERVAL = 2000;
