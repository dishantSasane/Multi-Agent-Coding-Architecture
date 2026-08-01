export interface TaskStatus {
  status:
    | 'PENDING'
    | 'INTENT_ANALYZING'
    | 'AWAITING_CONFIRMATION'
    | 'CONFIRMED'
    | 'DECOMPOSING'
    | 'GENERATING'
    | 'DEBATING'
    | 'SYNTHESIZING'
    | 'VALIDATING'
    | 'SANDBOX_EXECUTING'
    | 'CORRECTING'
    | 'COMPLETED'
    | 'FAILED';
}

export interface ModelActivity {
  model: string;
  status: 'waiting' | 'generating' | 'reviewing' | 'done' | 'failed';
  progress: number;
  latency?: number;
  tokens?: number;
  currentOutput?: string;
}

export interface ClarifyingQuestion {
  id: string;
  question: string;
  answer?: string;
  answerType: 'text' | 'boolean' | 'select';
  options?: string[];
}

export interface IntentAnalysis {
  summary: string;
  tech_stack: string[];
  requirements: string[];
  constraints: string[];
  edge_cases: string[];
  security_concerns: string[];
  clarifying_questions: ClarifyingQuestion[];
  confidence_score: number;
}

export interface FileNode {
  name: string;
  path: string;
  content: string;
  language: string;
  isDirectory: boolean;
  children?: FileNode[];
}

export interface ValidationStage {
  stage: 'syntax' | 'static_analysis' | 'security' | 'unit_tests' | 'property_tests';
  passed: boolean;
  details: string;
  errors?: string[];
  duration_ms?: number;
}

export interface ValidationReport {
  stages: ValidationStage[];
  overall_passed: boolean;
  coverage_percentage?: number;
  total_tests?: number;
  passed_tests?: number;
  failed_tests?: number;
}

export interface ModelOutput {
  model: string;
  code: string;
  reasoning: string;
  confidence: number;
  estimated_complexity: number;
  critique?: string;
  scores?: {
    correctness: number;
    security: number;
    performance: number;
    maintainability: number;
  };
}

export interface DebateResult {
  critiques: Array<{
    model: string;
    target_model: string;
    critique: string;
    scores: {
      correctness: number;
      security: number;
      performance: number;
      maintainability: number;
    };
  }>;
  consensus_reached: boolean;
  resolution?: string;
}

export interface TaskResult {
  files: FileNode[];
  code: string;
  tests: string;
  documentation: string;
  validation_report: ValidationReport;
  model_outputs: ModelOutput[];
  debate_result?: DebateResult;
  reasoning: string;
  known_limitations: string[];
}

export interface Task {
  id: string;
  query: string;
  status: TaskStatus['status'];
  progress: number;
  current_stage: string;
  intent_analysis?: IntentAnalysis;
  clarifying_questions: ClarifyingQuestion[];
  model_activity: ModelActivity[];
  result: TaskResult | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface WebSocketMessage {
  type:
    | 'status_update'
    | 'model_progress'
    | 'validation_result'
    | 'completed'
    | 'error'
    | 'debate_update';
  task_id?: string;
  status?: TaskStatus['status'];
  progress?: number;
  message?: string;
  model?: string;
  stage?: string;
  passed?: boolean;
  details?: string;
}

export interface AppSettings {
  backend_url: string;
  api_keys: {
    openai?: string;
    anthropic?: string;
    kimi?: string;
    qwen?: string;
    gemini?: string;
  };
  ensemble_models: string[];
  ensemble_size: number;
  model_timeout: number;
  sandbox_timeout: number;
  sandbox_memory_limit: string;
  sandbox_cpu_limit: number;
  sandbox_enable_network: boolean;
  theme: 'dark' | 'light' | 'system';
  editor_font_size: number;
  editor_word_wrap: boolean;
}

export const DEFAULT_SETTINGS: AppSettings = {
  backend_url: 'http://localhost:8000',
  api_keys: {},
  ensemble_models: ['claude', 'gpt-4o', 'qwen'],
  ensemble_size: 3,
  model_timeout: 30,
  sandbox_timeout: 30,
  sandbox_memory_limit: '512m',
  sandbox_cpu_limit: 1.0,
  sandbox_enable_network: false,
  theme: 'dark',
  editor_font_size: 14,
  editor_word_wrap: false,
};

export const STAGE_ORDER: TaskStatus['status'][] = [
  'PENDING',
  'INTENT_ANALYZING',
  'AWAITING_CONFIRMATION',
  'CONFIRMED',
  'DECOMPOSING',
  'GENERATING',
  'DEBATING',
  'SYNTHESIZING',
  'VALIDATING',
  'SANDBOX_EXECUTING',
  'CORRECTING',
  'COMPLETED',
];

export const MODEL_ICONS: Record<string, string> = {
  claude: '🟣',
  'gpt-4o': '🟢',
  qwen: '🔵',
  kimi: '🟡',
  gemini: '🟠',
};
