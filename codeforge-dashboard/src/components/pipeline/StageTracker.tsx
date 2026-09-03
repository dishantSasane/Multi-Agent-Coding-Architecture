import React from 'react';
import { motion } from 'framer-motion';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { STAGES } from '@/lib/constants';

interface StageTrackerProps {
  currentStage: string;
  completedStages?: string[];
  failedStage?: string | null;
}

export function StageTracker({
  currentStage,
  completedStages = [],
  failedStage = null,
}: StageTrackerProps) {
  const currentIndex = STAGES.findIndex((s) => s.id === currentStage);

  return (
    <div className="w-full overflow-x-auto pb-4">
      <div className="flex items-center min-w-max">
        {STAGES.map((stage, index) => {
          const isCompleted = completedStages.includes(stage.id) || index < currentIndex;
          const isActive = stage.id === currentStage && !failedStage;
          const isFailed = stage.id === failedStage;
          const Icon = stage.icon;

          return (
            <React.Fragment key={stage.id}>
              <motion.div
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: index * 0.05 }}
                className="flex flex-col items-center"
              >
                <div
                  className={cn(
                    'w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all',
                    isCompleted
                      ? 'bg-emerald-600 border-emerald-600 text-white'
                      : isActive
                      ? 'border-indigo-500 text-indigo-500'
                      : isFailed
                      ? 'bg-rose-600 border-rose-600 text-white'
                      : 'border-slate-700 text-slate-600'
                  )}
                >
                  {isFailed ? (
                    <XCircle className="w-5 h-5" />
                  ) : isCompleted ? (
                    <CheckCircle className="w-5 h-5" />
                  ) : isActive ? (
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                    >
                      <Loader2 className="w-5 h-5" />
                    </motion.div>
                  ) : (
                    <span className="text-lg">{Icon}</span>
                  )}
                </div>
                <span
                  className={cn(
                    'text-xs mt-2 font-medium whitespace-nowrap',
                    isActive ? 'text-indigo-400' : isCompleted ? 'text-emerald-400' : 'text-slate-500'
                  )}
                >
                  {stage.label}
                </span>
              </motion.div>

              {index < STAGES.length - 1 && (
                <div
                  className={cn(
                    'w-12 h-0.5 mx-2',
                    index < currentIndex ? 'bg-emerald-600' : 'bg-slate-700'
                  )}
                />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}
