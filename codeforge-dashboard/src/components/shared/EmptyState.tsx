import React from 'react';
import { Inbox } from 'lucide-react';

interface EmptyStateProps {
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
}

export function EmptyState({
  title = 'No data',
  description = 'There is nothing to show here yet.',
  icon,
  action,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center px-4 py-12 text-center">
      <div className="mb-4 text-muted-foreground" aria-hidden="true">
        {icon || <Inbox className="h-8 w-8" />}
      </div>
      <h2 className="mb-2 text-lg font-medium">{title}</h2>
      <p className="mb-4 max-w-sm text-sm text-muted-foreground">{description}</p>
      {action && <div>{action}</div>}
    </div>
  );
}
