import React, { useState } from 'react';
import { Send } from 'lucide-react';
import { Button } from '@/components/shared/Button';
import { MAX_QUERY_LENGTH } from '@/lib/constants';
import { cn } from '@/lib/utils';

interface QueryInputProps {
  onSubmit: (query: string) => void;
  /** Locks the form while the backend is working on the previous request. */
  isBusy?: boolean;
}

export function QueryInput({ onSubmit, isBusy = false }: QueryInputProps) {
  const [query, setQuery] = useState('');

  const isOverLimit = query.length > MAX_QUERY_LENGTH;
  const canSubmit = query.trim() !== '' && !isBusy && !isOverLimit;

  const submit = () => {
    if (!canSubmit) return;
    onSubmit(query.trim());
    setQuery('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
      className="rounded-lg border bg-card shadow-card transition-colors duration-150 ease-out focus-within:border-accent"
    >
      <label htmlFor="query" className="sr-only">
        Describe what you want to build
      </label>
      <textarea
        id="query"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="A FastAPI authentication system with JWT and Redis caching"
        rows={5}
        disabled={isBusy}
        className="block min-h-[160px] w-full resize-y rounded-t-lg bg-transparent p-4 text-base placeholder:text-muted-foreground focus:outline-none disabled:opacity-50"
      />
      <div className="flex items-center justify-between gap-4 border-t p-4">
        <span className={cn('text-xs', isOverLimit ? 'text-destructive' : 'text-muted-foreground')}>
          {query.length}/{MAX_QUERY_LENGTH}
          <span className="hidden sm:inline"> · Ctrl+Enter to submit</span>
        </span>
        <Button type="submit" disabled={!canSubmit} isLoading={isBusy}>
          <Send className="h-4 w-4" aria-hidden="true" />
          {isBusy ? 'Working…' : 'Generate code'}
        </Button>
      </div>
    </form>
  );
}
