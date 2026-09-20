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

export interface IntentAnalysis {
  summary: string;
  tech_stack: string[];
  requirements: string[];
  constraints: string[];
  edge_cases: string[];
  security_concerns: string[];
  clarifying_questions: string[];
  confidence_score: number;
  task_type?: string;
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
  stage: string;
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

export interface CodeFile {
  filename: string;
  content: string;
  language?: string;
  file_type?: string;
}

export interface Task {
  id: string;
  query: string;
  status: TaskStatus['status'];
  progress: number;
  current_stage: string;
  intent_analysis?: IntentAnalysis;
  clarifying_questions: string[];
  model_activity: ModelActivity[];
  result: TaskResult | null;
  error: string | null;
  created_at: string;
  updated_at: string;
  // Generated code — populated from /status once pipeline completes
  synthesized_code?: string | null;
  final_code?: string | null;
  // Multi-file output — null/undefined when result is a single file
  code_files?: CodeFile[] | null;
  validation_results?: Array<{
    stage: string;
    passed: boolean;
    errors?: string[];
    warnings?: string[];
    duration_ms?: number;
  }> | null;
  last_error?: string | null;
  correction_attempts?: number;
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
  editor_font_size: 14,
  editor_word_wrap: false,
};
