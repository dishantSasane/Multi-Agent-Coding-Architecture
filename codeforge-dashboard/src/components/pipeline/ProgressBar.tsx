import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

interface ProgressBarProps {
  progress: number;
  label?: string;
  showPercentage?: boolean;
  size?: 'sm' | 'md' | 'lg';
  animated?: boolean;
}

export function ProgressBar({
  progress = 0,
  label,
  showPercentage = true,
  size = 'md',
  animated = true,
}: ProgressBarProps) {
  const heightClasses = {
    sm: 'h-1.5',
    md: 'h-3',
    lg: 'h-4',
  };

  const clampedProgress = Math.min(Math.max(progress, 0), 100);

  return (
    <div className="w-full">
      {(label || showPercentage) && (
        <div className="flex justify-between mb-2">
          {label && <span className="text-sm font-medium">{label}</span>}
          {showPercentage && (
            <span className="text-sm text-slate-400">{Math.round(clampedProgress)}%</span>
          )}
        </div>
      )}
      
      <div className={cn('w-full bg-slate-800 rounded-full overflow-hidden', heightClasses[size])}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${clampedProgress}%` }}
          transition={{ duration: animated ? 0.5 : 0 }}
          className={cn(
            'h-full rounded-full',
            clampedProgress === 100
              ? 'bg-gradient-to-r from-emerald-500 to-emerald-600'
              : 'bg-gradient-to-r from-indigo-500 to-purple-600'
          )}
          style={{
            backgroundImage: animated && clampedProgress < 100
              ? 'linear-gradient(90deg, #6366f1 25%, #8b5cf6 50%, #6366f1 75%)'
              : undefined,
            backgroundSize: '200% 100%',
            animation: animated && clampedProgress < 100 ? 'shimmer 1.5s infinite' : undefined,
          }}
        />
      </div>
      
      <style>{`
        @keyframes shimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}</style>
    </div>
  );
}
