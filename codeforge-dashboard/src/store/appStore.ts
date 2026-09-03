import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { Task, AppSettings, DEFAULT_SETTINGS } from '@/types';

interface AppState {
  tasks: Task[];
  currentTaskId: string | null;
  settings: AppSettings;
  connectionStatus: 'online' | 'offline' | 'checking';
  
  // Actions
  addTask: (task: Task) => void;
  updateTask: (id: string, updates: Partial<Task>) => void;
  setCurrentTask: (id: string | null) => void;
  updateSettings: (settings: Partial<AppSettings>) => void;
  setConnectionStatus: (status: 'online' | 'offline' | 'checking') => void;
  deleteTask: (id: string) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      tasks: [],
      currentTaskId: null,
      settings: DEFAULT_SETTINGS,
      connectionStatus: 'checking',
      
      addTask: (task) =>
        set((state) => ({
          tasks: [task, ...state.tasks],
          currentTaskId: task.id,
        })),
      
      updateTask: (id, updates) =>
        set((state) => ({
          tasks: state.tasks.map((task) =>
            task.id === id ? { ...task, ...updates, updated_at: new Date().toISOString() } : task
          ),
        })),
      
      setCurrentTask: (id) => set({ currentTaskId: id }),
      
      updateSettings: (newSettings) =>
        set((state) => ({
          settings: { ...state.settings, ...newSettings },
        })),
      
      setConnectionStatus: (status) => set({ connectionStatus: status }),
      
      deleteTask: (id) =>
        set((state) => ({
          tasks: state.tasks.filter((task) => task.id !== id),
          currentTaskId: state.currentTaskId === id ? null : state.currentTaskId,
        })),
    }),
    {
      name: 'codeforge-storage',
      partialize: (state) => ({
        tasks: state.tasks,
        settings: state.settings,
      }),
    }
  )
);
