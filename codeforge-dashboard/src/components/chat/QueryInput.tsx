import React, { useState, useRef } from 'react';
import { Send } from 'lucide-react';
import { Button } from '@/components/shared/Button';
import { MAX_QUERY_LENGTH } from '@/lib/constants';

interface QueryInputProps {
  onSubmit: (query: string) => void;
  isLoading?: boolean;
}

export function QueryInput({ onSubmit, isLoading = false }: QueryInputProps) {
  const [query, setQuery] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = () => {
    if (!query.trim() || isLoading) return;
    onSubmit(query.trim());
    setQuery('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const characterCount = query.length;
  const isOverLimit = characterCount > MAX_QUERY_LENGTH;

  return (
    <div className="w-full max-w-4xl mx-auto">
      <div className="relative bg-slate-900 rounded-xl border border-slate-800 overflow-hidden focus-within:border-indigo-500 transition-colors">
        <textarea
          ref={textareaRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Describe what you want to build... (e.g., 'A FastAPI authentication system with JWT and Redis caching')"
          className="w-full min-h-[120px] max-h-[300px] p-4 bg-transparent resize-none focus:outline-none text-base leading-relaxed"
          rows={4}
          disabled={isLoading}
        />
        
        <div className="flex items-center justify-between p-4 border-t border-slate-800 bg-slate-900/50">
          <span className={`text-sm ${isOverLimit ? 'text-rose-500' : 'text-slate-400'}`}>
            {characterCount}/{MAX_QUERY_LENGTH}
          </span>
          
          <Button
            onClick={handleSubmit}
            disabled={!query.trim() || isLoading || isOverLimit}
            isLoading={isLoading}
          >
            <Send className="w-4 h-4 mr-2" />
            Generate Code
          </Button>
        </div>
      </div>
      
      <p className="text-center text-sm text-slate-500 mt-3">
        Press Ctrl+Enter to submit
      </p>
    </div>
  );
}
