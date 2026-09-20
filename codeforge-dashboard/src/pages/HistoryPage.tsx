import { Clock, Trash2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { EmptyState } from '@/components/shared/EmptyState';
import { useAppStore } from '@/store/appStore';
import { cn } from '@/lib/utils';

export function HistoryPage() {
  const tasks = useAppStore((s) => s.tasks);
  const setCurrentTask = useAppStore((s) => s.setCurrentTask);
  const deleteTask = useAppStore((s) => s.deleteTask);
  const navigate = useNavigate();

  if (tasks.length === 0) {
    return (
      <EmptyState
        icon={<Clock className="h-8 w-8" />}
        title="No history yet"
        description="Tasks you run will appear here."
      />
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">History</h1>
      <ul className="divide-y rounded-lg border bg-card shadow-card">
        {tasks.map((task) => {
          const status = task.status.toUpperCase();
          return (
            <li key={task.id} className="flex items-center gap-2 pr-2">
              <button
                type="button"
                onClick={() => {
                  setCurrentTask(task.id);
                  navigate('/');
                }}
                className="min-w-0 flex-1 rounded-lg p-4 text-left transition-colors duration-150 ease-out hover:bg-secondary active:bg-secondary/70"
              >
                <span className="block truncate text-base font-medium">{task.query}</span>
                <span className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                  <span
                    className={cn(
                      'font-medium',
                      status === 'COMPLETED' && 'text-success',
                      status === 'FAILED' && 'text-destructive'
                    )}
                  >
                    {status.replace(/_/g, ' ').toLowerCase()}
                  </span>
                  <span aria-hidden="true">·</span>
                  <span>{new Date(task.created_at).toLocaleString()}</span>
                </span>
              </button>
              <button
                type="button"
                onClick={() => deleteTask(task.id)}
                aria-label={`Delete task: ${task.query}`}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors duration-150 ease-out hover:bg-secondary hover:text-destructive active:bg-secondary/70"
              >
                <Trash2 className="h-4 w-4" aria-hidden="true" />
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
