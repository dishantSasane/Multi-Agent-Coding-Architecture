import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp, MessageSquare, Shield, Zap, Code, Star } from 'lucide-react';
import type { DebateResult } from '@/types';
import { cn } from '@/lib/utils';

interface DebateViewProps {
  debateResult?: DebateResult;
  isExpanded?: boolean;
}

export function DebateView({ debateResult, isExpanded = true }: DebateViewProps) {
  const [expanded, setExpanded] = useState(isExpanded);

  if (!debateResult) return null;

  const scoreLabels = {
    correctness: 'Correctness',
    security: 'Security',
    performance: 'Performance',
    maintainability: 'Maintainability',
  };

  const scoreIcons = {
    correctness: Code,
    security: Shield,
    performance: Zap,
    maintainability: MessageSquare,
  };

  return (
    <div className="border border-slate-800 rounded-xl overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 bg-slate-900 hover:bg-slate-800/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <MessageSquare className="w-5 h-5 text-indigo-500" />
          <h3 className="font-semibold">Model Debate & Review</h3>
          {!debateResult.consensus_reached && (
            <span className="px-2 py-0.5 bg-amber-500/10 text-amber-500 text-xs rounded-full">
              No Consensus
            </span>
          )}
        </div>
        {expanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="p-4 space-y-4">
              {/* Critiques */}
              {debateResult.critiques.map((critique, index) => {
                const Icon = scoreIcons.correctness;
                
                return (
                  <div
                    key={index}
                    className="p-4 bg-slate-950 rounded-lg border border-slate-800"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <span className="font-medium capitalize">{critique.model}</span>
                        <span className="text-slate-500">→</span>
                        <span className="text-slate-400 capitalize">
                          Reviewing {critique.target_model}
                        </span>
                      </div>
                    </div>

                    {/* Scores */}
                    <div className="grid grid-cols-2 gap-2 mb-3">
                      {Object.entries(critique.scores).map(([key, score]) => {
                        const ScoreIcon = scoreIcons[key as keyof typeof scoreIcons] || Star;
                        const scoreColor =
                          score >= 8 ? 'text-emerald-500' : score >= 6 ? 'text-amber-500' : 'text-rose-500';

                        return (
                          <div key={key} className="flex items-center gap-2 text-sm">
                            <ScoreIcon className="w-4 h-4 text-slate-500" />
                            <span className="text-slate-400">{scoreLabels[key as keyof typeof scoreLabels]}</span>
                            <span className={cn('ml-auto font-medium', scoreColor)}>
                              {score}/10
                            </span>
                          </div>
                        );
                      })}
                    </div>

                    {/* Critique Text */}
                    <p className="text-sm text-slate-300 whitespace-pre-wrap">{critique.critique}</p>
                  </div>
                );
              })}

              {/* Resolution */}
              {debateResult.resolution && (
                <div className="p-4 bg-indigo-500/10 border border-indigo-500/20 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <Star className="w-5 h-5 text-indigo-500" />
                    <h4 className="font-medium text-indigo-400">Resolution</h4>
                  </div>
                  <p className="text-sm text-slate-300">{debateResult.resolution}</p>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
