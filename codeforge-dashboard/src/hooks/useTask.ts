import { useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  confirmTask,
  getTaskStatus,
  submitQuery,
  testConnection,
  type TaskSnapshot,
} from '@/lib/api';
import { useAppStore } from '@/store/appStore';
import type { Task } from '@/types';

const POLL_MS = 2000;
// The backend stops on its own at these; anything else is still working.
const SETTLED: Task['status'][] = ['AWAITING_CONFIRMATION', 'COMPLETED', 'FAILED'];

const toStorePatch = (s: TaskSnapshot): Partial<Task> => ({
  status: s.status,
  current_stage: s.status,
  intent_analysis: s.intent_analysis ?? undefined,
  clarifying_questions: s.clarifying_questions ?? [],
  synthesized_code: s.synthesized_code ?? null,
  final_code: s.final_code ?? null,
  code_files: s.code_files ?? null,
  validation_results: s.validation_results ?? null,
  correction_attempts: s.correction_attempts,
  last_error: s.last_error ?? null,
  error: s.last_error ?? null,
});

/** Polls /status while the pipeline runs; stops when it needs the user or has finished. */
export function useTask(id: string | null) {
  const updateTask = useAppStore((s) => s.updateTask);
  const query = useQuery({
    queryKey: ['task', id],
    queryFn: () => getTaskStatus(id as string),
    enabled: id !== null,
    retry: 1,
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      return status && SETTLED.includes(status) ? false : POLL_MS;
    },
  });

  // Keep the persisted History list in step with the server
  useEffect(() => {
    if (id && query.data) updateTask(id, toStorePatch(query.data));
  }, [id, query.data, updateTask]);

  return query;
}

export function useSubmitTask() {
  const addTask = useAppStore((s) => s.addTask);
  return useMutation({
    mutationFn: async (query: string) => ({ query, res: await submitQuery(query) }),
    onSuccess: ({ query, res }) =>
      addTask({
        id: res.task_id,
        query,
        status: res.status.toUpperCase() as Task['status'],
        progress: 0,
        current_stage: 'PENDING',
        clarifying_questions: [],
        model_activity: [],
        result: null,
        error: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }),
  });
}

/** confirmed=true resumes generation; false re-analyses using the clarifications text. */
export function useConfirmTask(id: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { confirmed: boolean; clarifications?: string }) =>
      confirmTask(id as string, v.confirmed, v.clarifications),
    // Writing the new status into the cache restarts polling
    onSuccess: (snapshot) => qc.setQueryData(['task', id], snapshot),
  });
}

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: testConnection,
    refetchInterval: 30_000,
    retry: false,
  });
}
