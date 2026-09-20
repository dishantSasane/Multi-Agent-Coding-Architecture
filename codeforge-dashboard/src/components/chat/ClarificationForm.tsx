import { useState } from 'react';
import type { IntentAnalysis } from '@/types';
import { Button } from '@/components/shared/Button';

interface ClarificationFormProps {
  intentAnalysis?: IntentAnalysis;
  questions: string[];
  /** confirmed=true resumes generation; false re-analyses with the clarifications text. */
  onSubmit: (confirmed: boolean, clarifications?: string) => void;
  isBusy?: boolean;
}

function List({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <dt className="text-muted-foreground">{title}</dt>
      <dd>
        <ul className="list-inside list-disc">
          {items.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
      </dd>
    </div>
  );
}

export function ClarificationForm({
  intentAnalysis,
  questions,
  onSubmit,
  isBusy = false,
}: ClarificationFormProps) {
  const [clarifications, setClarifications] = useState('');

  return (
    <div className="space-y-6">
      {intentAnalysis && (
        <dl className="space-y-4 text-sm">
          <div>
            <dt className="text-muted-foreground">Understood as</dt>
            <dd>{intentAnalysis.summary}</dd>
          </div>
          {intentAnalysis.tech_stack.length > 0 && (
            <div>
              <dt className="text-muted-foreground">Tech stack</dt>
              <dd>{intentAnalysis.tech_stack.join(', ')}</dd>
            </div>
          )}
          <List title="Requirements" items={intentAnalysis.requirements} />
          <List title="Constraints" items={intentAnalysis.constraints} />
          <List title="Security concerns" items={intentAnalysis.security_concerns} />
          <div>
            <dt className="text-muted-foreground">Confidence</dt>
            <dd>{Math.round(intentAnalysis.confidence_score * 100)}%</dd>
          </div>
        </dl>
      )}

      {questions.length > 0 && (
        <div className="text-sm">
          <p className="mb-2 text-muted-foreground">Questions from the analyser</p>
          <ol className="list-inside list-decimal space-y-2">
            {questions.map((q, i) => (
              <li key={i}>{q}</li>
            ))}
          </ol>
        </div>
      )}

      <div>
        <label htmlFor="clarifications" className="mb-2 block text-sm text-muted-foreground">
          Answers or corrections (optional when confirming)
        </label>
        <textarea
          id="clarifications"
          value={clarifications}
          onChange={(e) => setClarifications(e.target.value)}
          rows={3}
          className="w-full rounded-lg border border-input bg-background p-4 text-sm focus:border-accent focus:outline-none"
        />
      </div>

      <div className="flex flex-col gap-4 sm:flex-row">
        <Button onClick={() => onSubmit(true, clarifications)} isLoading={isBusy}>
          Confirm and generate
        </Button>
        <Button
          variant="secondary"
          onClick={() => onSubmit(false, clarifications)}
          disabled={isBusy || clarifications.trim() === ''}
        >
          Re-analyse with my answers
        </Button>
      </div>
    </div>
  );
}
