import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import type { ModelActivity } from '@/types';
import { MODEL_ICONS } from '@/types';

interface ModelActivityCardProps {
  activity: ModelActivity;
}

export function ModelActivityCard({ activity }: ModelActivityCardProps) {
  const statusConfig = {
    waiting: { color: 'text-slate-400', bg: 'bg-slate-800' },
    generating: { color: 'text-indigo-400', bg: 'bg-indigo-500/10' },
    reviewing: { color: 'text-amber-400', bg: 'bg-amber-500/10' },
    done: { color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
    failed: { color: 'text-rose-400', bg: 'bg-rose-500/10' },
  };

  const config = statusConfig[activity.status];
  const icon = MODEL_ICONS[activity.model] || '⚪';

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className={cn(
        'p-4 rounded-xl border transition-all hover:shadow-lg',
        config.bg,
        'border-slate-800'
      )}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-xl">{icon}</span>
          <div>
            <h4 className="font-medium capitalize">{activity.model}</h4>
            <p className={cn('text-xs', config.color)}>
              {activity.status === 'generating' && 'Generating...'}
              {activity.status === 'reviewing' && 'Reviewing...'}
              {activity.status === 'done' && 'Completed'}
              {activity.status === 'failed' && 'Failed'}
              {activity.status === 'waiting' && 'Waiting'}
            </p>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-3">
        <div className="flex justify-between text-xs mb-1">
          <span className="text-slate-400">Progress</span>
          <span>{activity.progress}%</span>
        </div>
        <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${activity.progress}%` }}
            transition={{ duration: 0.3 }}
            className={cn(
              'h-full rounded-full',
              activity.status === 'failed'
                ? 'bg-rose-600'
                : activity.status === 'done'
                ? 'bg-emerald-600'
                : 'bg-indigo-600'
            )}
          />
        </div>
      </div>

      {/* Stats */}
      {(activity.latency || activity.tokens) && (
        <div className="flex gap-4 text-xs text-slate-400">
          {activity.latency && <span>⏱️ {activity.latency}ms</span>}
          {activity.tokens && <span>📝 {activity.tokens} tokens</span>}
        </div>
      )}

      {/* Current Output Snippet */}
      {activity.currentOutput && (
        <div className="mt-3 p-2 bg-slate-950 rounded-lg text-xs font-mono text-slate-300 max-h-20 overflow-hidden">
          {activity.currentOutput.slice(0, 100)}...
        </div>
      )}
    </motion.div>
  );
}
