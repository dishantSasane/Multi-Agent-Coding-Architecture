import { useState, useCallback } from 'react';
import { submitQuery, confirmTask as apiConfirmTask } from '@/lib/api';
import type { Task, ClarifyingQuestion } from '@/types';

interface UseCodeGenerationReturn {
  task: Task | null;
  isLoading: boolean;
  error: Error | null;
  submitQuery: (query: string) => Promise<void>;
  submitConfirmation: (answers: Array<{ question_id: string; answer: string | boolean }>) => Promise<void>;
}

export function useCodeGeneration(): UseCodeGenerationReturn {
  const [task, setTask] = useState<Task | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const submitQueryHandler = useCallback(async (query: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await submitQuery(query);
      
      setTask({
        id: response.task_id,
        query,
        status: response.status as Task['status'],
        progress: 0,
        current_stage: 'PENDING',
        clarifying_questions: [],
        model_activity: [],
        result: null,
        error: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
    } catch (e) {
      setError(e instanceof Error ? e : new Error('Failed to submit query'));
      throw e;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const submitConfirmation = useCallback(
    async (answers: Array<{ question_id: string; answer: string | boolean }>) => {
      if (!task) throw new Error('No active task');

      setIsLoading(true);
      setError(null);

      try {
        const updatedTask = await apiConfirmTask(task.id, answers, true);
        setTask(updatedTask);
      } catch (e) {
        setError(e instanceof Error ? e : new Error('Failed to submit confirmation'));
        throw e;
      } finally {
        setIsLoading(false);
      }
    },
    [task]
  );

  return {
    task,
    isLoading,
    error,
    submitQuery: submitQueryHandler,
    submitConfirmation,
  };
}
