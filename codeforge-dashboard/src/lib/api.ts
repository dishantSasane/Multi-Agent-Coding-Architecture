import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { useAppStore } from '@/store/appStore';
import type { Task, TaskResult } from '@/types';

const getBaseUrl = () => {
  const stored = localStorage.getItem('codeforge-backend-url');
  // If a custom URL is stored and it's not localhost:5173 (the dev server itself),
  // use it directly. Otherwise use an empty string so requests go through the
  // Vite proxy (/api → http://localhost:8000) and avoid CORS entirely.
  if (stored && !stored.includes('localhost:5173') && !stored.includes('127.0.0.1:5173')) {
    return stored;
  }
  return '';
};

const api = axios.create({
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add correlation ID and update base URL
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  config.baseURL = getBaseUrl();
  
  const correlationId = `corr_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
  config.headers['X-Correlation-ID'] = correlationId;
  
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.code === 'ERR_NETWORK') {
      useAppStore.getState().setConnectionStatus('offline');
    }
    
    let message = 'An unexpected error occurred';
    
    if (error.response) {
      const data = error.response.data as Record<string, unknown>;
      message = (data.message as string) || (data.detail as string) || message;
    } else if (error.request) {
      message = 'No response from server. Please check if the backend is running.';
    } else {
      message = error.message;
    }
    
    return Promise.reject(new Error(message));
  }
);

export interface SubmitQueryRequest {
  query: string;
  context?: Record<string, unknown>;
  preferences?: {
    style?: string;
    testing?: string;
  };
}

export interface SubmitQueryResponse {
  task_id: string;
  status: string;
}

export const submitQuery = async (
  query: string,
  context?: Record<string, unknown>,
  preferences?: { style?: string; testing?: string }
): Promise<SubmitQueryResponse> => {
  const response = await api.post<SubmitQueryResponse>('/api/v1/query', {
    query,
    context,
    preferences,
  });
  return response.data;
};

// Shape returned by GET /status and POST /confirm (backend TaskStatusResponse).
// Status arrives lowercase ("awaiting_confirmation"); the UI uses uppercase.
export type TaskSnapshot = Omit<Partial<Task>, 'status'> & {
  status: Task['status'];
  user_query: string;
  correction_attempts: number;
};

const toSnapshot = (data: Record<string, unknown>): TaskSnapshot =>
  ({ ...data, status: String(data.status).toUpperCase() }) as TaskSnapshot;

export const getTaskStatus = async (taskId: string): Promise<TaskSnapshot> => {
  const response = await api.get(`/api/v1/query/${taskId}/status`);
  return toSnapshot(response.data);
};

/** confirmed=true resumes generation; false re-analyses with the clarifications. */
export const confirmTask = async (
  taskId: string,
  confirmed: boolean,
  clarifications?: string
): Promise<TaskSnapshot> => {
  const response = await api.post(`/api/v1/query/${taskId}/confirm`, {
    confirmed,
    clarifications: clarifications || null,
  });
  return toSnapshot(response.data);
};

export const getTaskResult = async (taskId: string): Promise<TaskResult> => {
  const response = await api.get<TaskResult>(`/api/v1/query/${taskId}/result`);
  return response.data;
};

export const testConnection = async (): Promise<boolean> => {
  try {
    await api.get('/api/v1/health');
    return true;
  } catch {
    return false;
  }
};

export const setBackendUrl = (url: string): void => {
  localStorage.setItem('codeforge-backend-url', url);
};

export const getBackendUrl = (): string => {
  return getBaseUrl();
};
