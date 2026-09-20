import { Bolt } from 'lucide-react';
import { QueryInput } from '@/components/chat/QueryInput';
import { ClarificationForm } from '@/components/chat/ClarificationForm';
import { StageTracker } from '@/components/pipeline/StageTracker';
import { FileTabs } from '@/components/code/FileTabs';
import { ValidationReport } from '@/components/validation/ValidationReport';
import { EmptyState } from '@/components/shared/EmptyState';
import { Button } from '@/components/shared/Button';
import { useAppStore } from '@/store/appStore';
import { useConfirmTask, useSubmitTask, useTask } from '@/hooks/useTask';
import { isBusy, phaseOf, type Phase } from '@/lib/phase';
import { downloadBlob } from '@/lib/utils';
import type { Task, ValidationReport as ValidationReportData } from '@/types';

const WAITING_TEXT: Partial<Record<Phase, string>> = {
  submitting: 'Sending your request…',
  analysing: 'Reading your request…',
  awaiting_confirmation: 'Waiting for your confirmation.',
  generating: 'Models are writing the code…',
  validating: 'Checking the code…',
};

const Card = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <section className="rounded-lg border bg-card p-6 shadow-card">
    <h2 className="mb-4 text-sm font-medium uppercase tracking-wider text-muted-foreground">{title}</h2>
    {children}
  </section>
);

function toReport(results: Task['validation_results']): ValidationReportData | null {
  if (!results?.length) return null;
  return {
    overall_passed: results.every((r) => r.passed),
    stages: results.map((r) => ({
      stage: r.stage,
      passed: r.passed,
      details: (r.passed ? r.warnings : r.errors)?.join('; ') ?? '',
      errors: r.errors,
      duration_ms: r.duration_ms,
    })),
  };
}

export function HomePage() {
  const currentTaskId = useAppStore((s) => s.currentTaskId);
  const task = useAppStore((s) => s.tasks.find((t) => t.id === currentTaskId) ?? null);

  const submit = useSubmitTask();
  const confirm = useConfirmTask(currentTaskId);
  const poll = useTask(currentTaskId);

  const phase = phaseOf(task?.status, submit.isPending);
  const error = submit.error ?? confirm.error ?? poll.error;
  const files = task?.code_files ?? null;
  const singleCode = task?.synthesized_code ?? task?.final_code ?? null;
  const report = toReport(task?.validation_results);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">New query</h1>
        <p className="mt-2 max-w-2xl text-base text-muted-foreground">
          Describe what you want to build. Several models draft and validate the code, and you
          confirm the plan before it is generated.
        </p>
      </div>

      {error && (
        <p role="alert" className="rounded-lg border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          {error.message}
        </p>
      )}

      <div className="grid gap-8 lg:grid-cols-12">
        <div className="space-y-8 lg:col-span-5">
          <QueryInput onSubmit={(q) => submit.mutate(q)} isBusy={isBusy(phase)} />

          {task && phase !== 'idle' && (
            <Card title="Progress">
              <p className="mb-4 line-clamp-2 text-sm text-muted-foreground">{task.query}</p>
              <StageTracker currentStage={task.status} />
            </Card>
          )}

          {phase === 'awaiting_confirmation' && task && (
            <Card title="Confirm before generating">
              <ClarificationForm
                intentAnalysis={task.intent_analysis}
                questions={task.clarifying_questions}
                isBusy={confirm.isPending}
                onSubmit={(confirmed, clarifications) => confirm.mutate({ confirmed, clarifications })}
              />
            </Card>
          )}
        </div>

        <div className="space-y-8 lg:col-span-7">
          {phase === 'idle' ? (
            <div className="min-h-[320px] rounded-lg border border-dashed">
              <EmptyState
                icon={<Bolt className="h-8 w-8" />}
                title="Nothing generated yet"
                description="Your files and validation results will appear here."
              />
            </div>
          ) : (
            <Card title="Generated code">
              {phase === 'failed' && (
                <p role="alert" className="mb-4 rounded-lg border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
                  Generation failed{task?.error ? `: ${task.error}` : '.'}
                </p>
              )}

              {files && files.length > 0 ? (
                <FileTabs key={task?.id} files={files} />
              ) : singleCode ? (
                <div className="space-y-4">
                  <div className="flex justify-end">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => downloadBlob(new Blob([singleCode], { type: 'text/plain' }), 'generated_code.txt')}
                    >
                      Download
                    </Button>
                  </div>
                  <pre tabIndex={0} className="max-h-[640px] min-h-[320px] overflow-auto rounded-lg bg-code p-4 text-sm text-code-foreground">
                    <code>{singleCode}</code>
                  </pre>
                </div>
              ) : (
                // Height is reserved so the layout does not jump when code arrives
                <div role="status" className="min-h-[320px] space-y-4 rounded-lg bg-secondary p-6">
                  <p className="text-sm text-muted-foreground">
                    {WAITING_TEXT[phase] ?? 'No code was produced.'}
                  </p>
                  {(isBusy(phase) || phase === 'awaiting_confirmation') && (
                    <>
                      <div className="h-4 w-3/4 rounded bg-border" />
                      <div className="h-4 w-1/2 rounded bg-border" />
                      <div className="h-4 w-2/3 rounded bg-border" />
                    </>
                  )}
                </div>
              )}
            </Card>
          )}

          {report && (
            <Card title="Validation">
              <ValidationReport report={report} />
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
