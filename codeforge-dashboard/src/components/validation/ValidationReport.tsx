import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle, XCircle, AlertTriangle, FileCode, Shield, FlaskConical } from 'lucide-react';
import type { ValidationReport } from '@/types';
import { cn } from '@/lib/utils';

interface ValidationReportProps {
  report?: ValidationReport;
}

export function ValidationReport({ report }: ValidationReportProps) {
  if (!report) {
    return (
      <div className="p-4 text-slate-500 text-center">
        No validation results available
      </div>
    );
  }

  const stageIcons = {
    syntax: FileCode,
    static_analysis: AlertTriangle,
    security: Shield,
    unit_tests: FlaskConical,
    property_tests: FlaskConical,
  };

  const passedCount = report.stages.filter((s) => s.passed).length;
  const totalCount = report.stages.length;

  return (
    <div className="space-y-3">
      {/* Summary */}
      <div
        className={cn(
          'p-4 rounded-xl border',
          report.overall_passed
            ? 'bg-emerald-500/10 border-emerald-500/20'
            : 'bg-rose-500/10 border-rose-500/20'
        )}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {report.overall_passed ? (
              <CheckCircle className="w-6 h-6 text-emerald-500" />
            ) : (
              <XCircle className="w-6 h-6 text-rose-500" />
            )}
            <div>
              <h3 className="font-semibold">
                {report.overall_passed ? 'All Validations Passed' : 'Validation Failed'}
              </h3>
              <p className="text-sm text-slate-400">
                {passedCount}/{totalCount} stages passed
              </p>
            </div>
          </div>
          
          {report.coverage_percentage && (
            <div className="text-right">
              <div className="text-2xl font-bold">{report.coverage_percentage}%</div>
              <div className="text-xs text-slate-400">Coverage</div>
            </div>
          )}
        </div>
      </div>

      {/* Stages */}
      <div className="space-y-2">
        {report.stages.map((stage, index) => {
          const Icon = stageIcons[stage.stage];
          
          return (
            <motion.div
              key={stage.stage}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className={cn(
                'p-3 rounded-lg border',
                stage.passed
                  ? 'bg-emerald-500/5 border-emerald-500/20'
                  : 'bg-rose-500/5 border-rose-500/20'
              )}
            >
              <div className="flex items-center gap-3 mb-2">
                {stage.passed ? (
                  <CheckCircle className="w-5 h-5 text-emerald-500" />
                ) : (
                  <XCircle className="w-5 h-5 text-rose-500" />
                )}
                <Icon className="w-5 h-5 text-slate-400" />
                <span className="font-medium capitalize">
                  {stage.stage.replace('_', ' ')}
                </span>
                {stage.duration_ms && (
                  <span className="ml-auto text-xs text-slate-400">
                    {stage.duration_ms}ms
                  </span>
                )}
              </div>
              
              <p className="text-sm text-slate-300 ml-8">{stage.details}</p>
              
              {stage.errors && stage.errors.length > 0 && (
                <div className="mt-2 ml-8 p-2 bg-slate-950 rounded text-xs font-mono text-rose-400 overflow-x-auto">
                  {stage.errors.map((error, i) => (
                    <div key={i}>{error}</div>
                  ))}
                </div>
              )}
            </motion.div>
          );
        })}
      </div>

      {/* Test Summary */}
      {(report.total_tests || report.passed_tests || report.failed_tests) && (
        <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
          <h4 className="font-medium mb-2">Test Summary</h4>
          <div className="flex gap-4 text-sm">
            <span className="text-emerald-400">✓ {report.passed_tests} passed</span>
            <span className="text-rose-400">✗ {report.failed_tests} failed</span>
            <span className="text-slate-400">⊘ {((report.total_tests || 0) - (report.passed_tests || 0) - (report.failed_tests || 0))} skipped</span>
          </div>
        </div>
      )}
    </div>
  );
}
