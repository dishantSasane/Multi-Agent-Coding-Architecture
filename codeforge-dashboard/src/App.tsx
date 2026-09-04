import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from '@/components/layout/Layout';
import { QueryInput } from '@/components/chat/QueryInput';
import { StageTracker } from '@/components/pipeline/StageTracker';
import { ModelActivityCard } from '@/components/pipeline/ModelActivityCard';
import { DebateView } from '@/components/pipeline/DebateView';
import { ValidationReport } from '@/components/validation/ValidationReport';
import { EmptyState } from '@/components/shared/EmptyState';
import { ErrorBoundary } from '@/components/shared/ErrorBoundary';
import { useAppStore } from '@/store/appStore';
import { useWebSocket } from '@/hooks/useWebSocket';
import { submitQuery, getTaskStatus } from '@/lib/api';
import { Bolt, Clock, Trash2 } from 'lucide-react';
import { Task, CodeFile } from '@/types';

// ─── Home / New Query Page ────────────────────────────────────────────────────
function HomePage() {
  const { tasks, currentTaskId, addTask, setCurrentTask, updateTask } = useAppStore();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Track the task id that the WebSocket should watch
  const [wsTaskId, setWsTaskId] = useState<string | null>(null);
  // Local copy of the generated code — set immediately when the /status fetch
  // resolves, bypassing any store-update race condition.
  const [generatedCode, setGeneratedCode] = useState<string | null>(null);
  // Local copy of multi-file results (mirrors task.code_files)
  const [generatedFiles, setGeneratedFiles] = useState<CodeFile[] | null>(null);
  // Active tab index for multi-file display
  const [activeFileIdx, setActiveFileIdx] = useState(0);

  const currentTask = tasks.find((t) => t.id === currentTaskId) ?? null;

  const detectExtension = (code: string): string => {
    if (code.includes('def ') || (code.includes('import ') && !code.includes('from '))) return 'py';
    if (code.includes('function ') || code.includes('const ') || code.includes('=>')) return 'js';
    if (code.includes('public class') || code.includes('public static void')) return 'java';
    return 'txt';
  };

  const downloadCode = () => {
    const code = currentTask?.synthesized_code ?? currentTask?.final_code ?? generatedCode;
    if (!code) return;
    const ext = detectExtension(code);
    const blob = new Blob([code], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `generated_code.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Connect WebSocket for the active task and update store on every message
  const { lastMessage } = useWebSocket(wsTaskId);

  useEffect(() => {
    if (!lastMessage || !wsTaskId) return;
    const { type, status, progress } = lastMessage as {
      type: string;
      status?: string;
      progress?: number;
    };

    if (type === 'status_update' || type === 'completed' || type === 'error') {
      // The WS sends two messages when a task finishes:
      //   MSG 1: {type:"status_update", status:"completed", ...}
      //   MSG 2: {type:"completed",                         ...}  ← NO status field
      // For MSG 2, `status` is undefined. Using `status ?? 'pending'` would reset
      // the stage tracker to PENDING and hide the completed code block.
      // Derive the correct uppercase value from `type` for terminal messages.
      const upperStatus: Task['status'] =
        type === 'completed' ? 'COMPLETED' :
        type === 'error'     ? 'FAILED'    :
        ((status ?? 'pending') as string).toUpperCase() as Task['status'];

      updateTask(wsTaskId, {
        status: upperStatus,
        current_stage: upperStatus,
        progress: type === 'completed' ? 100 : progress ?? 0,
        ...(type === 'error' ? { error: (lastMessage as { message?: string }).message ?? 'Unknown error' } : {}),
      });

      // Stop tracking once the task reaches a terminal state
      if (type === 'completed' || type === 'error') {
        const taskId = wsTaskId; // capture before state clears
        setIsLoading(false);
        setWsTaskId(null);

        // Fetch the full task to get the generated code
        if (type === 'completed') {
          console.log('[CodeForge] WS completed message received');
          getTaskStatus(taskId)
            .then((full) => {
              const raw = full as unknown as Record<string, unknown>;
              console.log('[CodeForge] /status response:', raw);
              const code =
                (raw.synthesized_code as string) || (raw.final_code as string) || null;
              const files = (raw.code_files as CodeFile[] | null) || null;
              // 1. Local state — renders immediately without waiting for the store
              setGeneratedCode(code);
              if (files && files.length >= 2) {
                setGeneratedFiles(files);
                setActiveFileIdx(0);
              }
              // 2. Store update — keeps history page / other consumers in sync
              updateTask(taskId, {
                synthesized_code: (raw.synthesized_code as string) || null,
                final_code: (raw.final_code as string) || null,
                code_files: files,
              });
            })
            .catch((err) => {
              console.error('[CodeForge] failed to fetch completed task:', err);
            });
        }
      }
    }
  }, [lastMessage, wsTaskId, updateTask]);

  const handleSubmit = async (query: string) => {
    setIsLoading(true);
    setError(null);
    // Reset code/file state so the new task starts clean
    setGeneratedCode(null);
    setGeneratedFiles(null);
    setActiveFileIdx(0);

    try {
      // Send the query to the real backend
      const response = await submitQuery(query);

      const newTask: Task = {
        id: response.task_id,
        query,
        status: (response.status ?? 'PENDING') as Task['status'],
        progress: 0,
        current_stage: 'PENDING',
        clarifying_questions: [],
        model_activity: [
          { model: 'claude',  status: 'waiting', progress: 0 },
          { model: 'gpt-4o',  status: 'waiting', progress: 0 },
          { model: 'qwen',    status: 'waiting', progress: 0 },
        ],
        result: null,
        error: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      addTask(newTask);
      setCurrentTask(newTask.id);
      // Open a WebSocket so we get real-time status updates
      setWsTaskId(newTask.id);
    } catch (e) {
      setIsLoading(false);
      setError(e instanceof Error ? e.message : 'Failed to submit query. Is the backend running?');
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Hero */}
      <div className="text-center pt-8 pb-4">
        <div className="flex items-center justify-center gap-3 mb-4">
          <Bolt className="w-10 h-10 text-indigo-500" />
          <h1 className="text-4xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
            CodeForge
          </h1>
        </div>
        <p className="text-slate-400 text-lg max-w-2xl mx-auto">
          Multi-Agent Coding Orchestrator — describe what you want to build and watch
          multiple AI models collaborate, debate, and deliver production-ready code.
        </p>
      </div>

      {/* Query Input */}
      <QueryInput onSubmit={handleSubmit} isLoading={isLoading} />

      {/* Submission error */}
      {error && (
        <div className="bg-rose-950/40 border border-rose-800 rounded-xl p-4 text-rose-300 text-sm">
          ⚠ {error}
        </div>
      )}

      {/* Active Task */}
      {currentTask && (
        <div className="space-y-6">
          {/* Stage Tracker */}
          <div className="bg-slate-900 rounded-xl border border-slate-800 p-6">
            <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
              Pipeline Progress
            </h2>
            <StageTracker currentStage={currentTask.status} />
          </div>

          {/* Generated Code — always visible once a task is active */}
          <div className="bg-slate-900 rounded-xl border border-slate-800 p-6 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
                Generated Code
              </h2>
              {/* Single-file download — shown only when no multi-file tabs */}
              {!(generatedFiles ?? currentTask.code_files)?.length &&
                (currentTask.synthesized_code || currentTask.final_code || generatedCode) && (
                  <button
                    onClick={downloadCode}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-indigo-600 text-slate-300 hover:text-white text-xs font-medium transition-colors"
                  >
                    ⬇ Download
                  </button>
                )}
            </div>

            {/* Running */}
            {currentTask.status !== 'COMPLETED' && currentTask.status !== 'FAILED' && (
              <div className="min-h-[300px] flex items-center justify-center bg-slate-950 rounded-lg border border-slate-700">
                <p className="text-slate-500 text-sm">⏳ Waiting for code generation…</p>
              </div>
            )}

            {/* Completed */}
            {currentTask.status === 'COMPLETED' && (() => {
              const codeFiles = generatedFiles ?? currentTask.code_files ?? null;
              const hasMultipleFiles = codeFiles && codeFiles.length >= 2;

              // ── Download-all-as-ZIP helper (lazy-loads jszip) ──────────────
              const downloadAllAsZip = async () => {
                const JSZip = (await import('jszip')).default;
                const zip = new JSZip();
                codeFiles!.forEach((f) => zip.file(f.filename, f.content));
                const blob = await zip.generateAsync({ type: 'blob' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'generated_project.zip';
                a.click();
                URL.revokeObjectURL(url);
              };

              // ── Single-file download helper ────────────────────────────────
              const downloadFile = (filename: string, content: string) => {
                const blob = new Blob([content], { type: 'text/plain' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                a.click();
                URL.revokeObjectURL(url);
              };

              if (hasMultipleFiles) {
                const activeFile = codeFiles![activeFileIdx] ?? codeFiles![0];
                return (
                  <div className="space-y-3">
                    {/* Tab bar + ZIP button */}
                    <div className="flex items-center gap-2 flex-wrap">
                      {codeFiles!.map((file, idx) => (
                        <button
                          key={file.filename}
                          onClick={() => setActiveFileIdx(idx)}
                          className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-colors ${
                            activeFileIdx === idx
                              ? 'bg-indigo-600 text-white'
                              : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200'
                          }`}
                        >
                          {file.filename}
                        </button>
                      ))}
                      <button
                        onClick={downloadAllAsZip}
                        className="ml-auto flex items-center gap-1 px-3 py-1.5 rounded-lg bg-emerald-700 hover:bg-emerald-600 text-white text-xs font-medium transition-colors"
                      >
                        ⬇ Download ZIP
                      </button>
                    </div>

                    {/* Active file */}
                    <div className="relative">
                      {/* Per-file download button */}
                      <div className="absolute top-2 right-2 z-10">
                        <button
                          onClick={() => downloadFile(activeFile.filename, activeFile.content)}
                          className="px-2 py-1 rounded bg-slate-700 hover:bg-slate-600 text-slate-300 hover:text-white text-xs transition-colors"
                        >
                          ⬇ {activeFile.filename}
                        </button>
                      </div>
                      <pre className="bg-slate-950 rounded-lg p-4 pt-10 overflow-x-auto text-sm text-slate-200 border border-slate-700 min-h-[300px] max-h-[800px] overflow-y-auto">
                        <code>{activeFile.content}</code>
                      </pre>
                    </div>
                  </div>
                );
              }

              // ── Single-file fallback ────────────────────────────────────────
              const singleCode = currentTask.synthesized_code ?? currentTask.final_code ?? generatedCode;
              if (singleCode) {
                return (
                  <pre className="bg-slate-950 rounded-lg p-4 overflow-x-auto text-sm text-slate-200 border border-slate-700 min-h-[300px] max-h-[800px] overflow-y-auto">
                    <code>{singleCode}</code>
                  </pre>
                );
              }

              return (
                <div className="min-h-[300px] flex items-center justify-center bg-slate-950 rounded-lg border border-slate-700">
                  <p className="text-slate-500 text-sm">✨ Fetching generated code…</p>
                </div>
              );
            })()}

            {/* Failed */}
            {currentTask.status === 'FAILED' && (
              <div className="min-h-[300px] flex items-center justify-center bg-rose-950/30 rounded-lg border border-rose-800">
                <p className="text-rose-400 text-sm">
                  ❌ Generation failed{currentTask.error ? `: ${currentTask.error}` : '.'}
                </p>
              </div>
            )}
          </div>

          {/* Model Activity */}
          {currentTask.model_activity.length > 0 && (
            <div className="bg-slate-900 rounded-xl border border-slate-800 p-6">
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
                Model Activity
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {currentTask.model_activity.map((m) => (
                  <ModelActivityCard key={m.model} activity={m} />
                ))}
              </div>
            </div>
          )}

          {/* Validation Report */}
          {currentTask.result?.validation_report && (
            <ValidationReport report={currentTask.result.validation_report} />
          )}

          {/* Debate View */}
          {currentTask.result?.debate_result && (
            <DebateView debateResult={currentTask.result.debate_result} />
          )}

        </div>
      )}

      {/* Empty state */}
      {!currentTask && !isLoading && (
        <EmptyState
          icon={<Bolt className="w-12 h-12 text-slate-600" />}
          title="Ready to build"
          description="Describe your coding task above and CodeForge will orchestrate multiple AI models to generate, review, and validate your code."
        />
      )}
    </div>
  );
}

// ─── History Page ─────────────────────────────────────────────────────────────
function HistoryPage() {
  const { tasks, setCurrentTask, deleteTask } = useAppStore();

  if (tasks.length === 0) {
    return (
      <EmptyState
        icon={<Clock className="w-12 h-12 text-slate-600" />}
        title="No history yet"
        description="Tasks you run will appear here."
      />
    );
  }

  const statusColor: Record<string, string> = {
    COMPLETED: 'text-emerald-400',
    FAILED: 'text-rose-400',
    PENDING: 'text-slate-400',
  };

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      <h1 className="text-2xl font-bold mb-6">Task History</h1>
      {tasks.map((task) => (
        <div
          key={task.id}
          className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex items-start justify-between gap-4 hover:border-indigo-700 transition-colors cursor-pointer"
          onClick={() => setCurrentTask(task.id)}
        >
          <div className="flex-1 min-w-0">
            <p className="font-medium truncate">{task.query}</p>
            <div className="flex items-center gap-3 mt-1 text-sm text-slate-500">
              <span className={statusColor[task.status] ?? 'text-amber-400'}>
                {task.status.replace(/_/g, ' ')}
              </span>
              <span>·</span>
              <span>{new Date(task.created_at).toLocaleString()}</span>
            </div>
          </div>
          <button
            onClick={(e) => { e.stopPropagation(); deleteTask(task.id); }}
            className="p-2 rounded-lg hover:bg-slate-800 text-slate-500 hover:text-rose-400 transition-colors flex-shrink-0"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      ))}
    </div>
  );
}

// ─── Settings Page ────────────────────────────────────────────────────────────
function SettingsPage() {
  const { settings, updateSettings } = useAppStore();

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">Settings</h1>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-5">
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Backend</h2>
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">Backend URL</label>
          <input
            type="text"
            value={settings.backend_url}
            onChange={(e) => updateSettings({ backend_url: e.target.value })}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-indigo-500 transition-colors"
          />
        </div>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-5">
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">API Keys</h2>
        {(['anthropic', 'openai', 'qwen', 'kimi', 'gemini'] as const).map((provider) => (
          <div key={provider}>
            <label className="block text-sm font-medium text-slate-300 mb-1 capitalize">
              {provider} API Key
            </label>
            <input
              type="password"
              placeholder={`sk-...`}
              value={settings.api_keys[provider] ?? ''}
              onChange={(e) =>
                updateSettings({ api_keys: { ...settings.api_keys, [provider]: e.target.value } })
              }
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-indigo-500 transition-colors font-mono"
            />
          </div>
        ))}
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-5">
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Sandbox</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Memory Limit</label>
            <input
              type="text"
              value={settings.sandbox_memory_limit}
              onChange={(e) => updateSettings({ sandbox_memory_limit: e.target.value })}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-indigo-500 transition-colors"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Timeout (s)</label>
            <input
              type="number"
              value={settings.sandbox_timeout}
              onChange={(e) => updateSettings({ sandbox_timeout: Number(e.target.value) })}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-indigo-500 transition-colors"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Root App ─────────────────────────────────────────────────────────────────
export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
