import { CheckCircle, XCircle } from 'lucide-react';
import type { ValidationReport as ValidationReportData } from '@/types';
import { formatDuration } from '@/lib/utils';

export function ValidationReport({ report }: { report: ValidationReportData }) {
  const passed = report.stages.filter((s) => s.passed).length;

  return (
    <div className="space-y-4">
      <p className="flex items-center gap-2 text-base font-medium">
        {report.overall_passed ? (
          <CheckCircle className="h-5 w-5 text-success" aria-hidden="true" />
        ) : (
          <XCircle className="h-5 w-5 text-destructive" aria-hidden="true" />
        )}
        {report.overall_passed ? 'All validations passed' : 'Validation failed'}
        <span className="text-sm font-normal text-muted-foreground">
          {passed}/{report.stages.length} stages
        </span>
      </p>

      <ul className="divide-y">
        {report.stages.map((stage) => (
          <li key={stage.stage} className="py-4">
            <div className="flex items-center gap-2 text-sm">
              {stage.passed ? (
                <CheckCircle className="h-4 w-4 shrink-0 text-success" aria-hidden="true" />
              ) : (
                <XCircle className="h-4 w-4 shrink-0 text-destructive" aria-hidden="true" />
              )}
              <span className="font-medium capitalize">{stage.stage.replace(/_/g, ' ')}</span>
              <span className="text-muted-foreground">{stage.passed ? 'Passed' : 'Failed'}</span>
              {stage.duration_ms != null && (
                <span className="ml-auto text-xs text-muted-foreground">{formatDuration(stage.duration_ms)}</span>
              )}
            </div>
            {stage.details && (
              <p className="mt-2 break-words pl-6 text-sm text-muted-foreground">{stage.details}</p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
