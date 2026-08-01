import { useState, useEffect, useCallback } from 'react';
import { getTaskStatus } from '@/lib/api';
import type { Task } from '@/types';
import { POLL_INTERVAL } from '@/lib/constants';

interface UseTaskPollingReturn {
  task: Task | null;
  isLoading: boolean;
  error: Error | null;
  stopPolling: () => void;
}

const TERMINAL_STATUSES = ['COMPLETED', 'FAILED'];

export function useTaskPolling(taskId: string | null): UseTaskPollingReturn {
  const [task, setTask] = useState<Task | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [shouldPoll, setShouldPoll] = useState(true);

  const fetchTask = useCallback(async () => {
    if (!taskId) return;
    
    try {
      const data = await getTaskStatus(taskId);
      setTask(data);
      setError(null);
      
      // Stop polling if task is in terminal state
      if (TERMINAL_STATUSES.includes(data.status)) {
        setShouldPoll(false);
      }
    } catch (e) {
      setError(e instanceof Error ? e : new Error('Failed to fetch task status'));
    } finally {
      setIsLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    if (!taskId || !shouldPoll) {
      return;
    }

    // Initial fetch
    fetchTask();

    // Set up polling interval
    const interval = setInterval(fetchTask, POLL_INTERVAL);

    return () => clearInterval(interval);
  }, [taskId, shouldPoll, fetchTask]);

  const stopPolling = useCallback(() => {
    setShouldPoll(false);
  }, []);

  return {
    task,
    isLoading,
    error,
    stopPolling,
  };
}
