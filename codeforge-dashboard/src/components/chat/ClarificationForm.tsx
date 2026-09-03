import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { CheckCircle, AlertCircle } from 'lucide-react';
import type { ClarifyingQuestion, IntentAnalysis } from '@/types';
import { Button } from '@/components/shared/Button';

interface ClarificationFormProps {
  questions: ClarifyingQuestion[];
  intentAnalysis?: IntentAnalysis;
  onConfirm: (answers: Array<{ question_id: string; answer: string | boolean }>) => void;
  isLoading?: boolean;
}

export function ClarificationForm({
  questions,
  intentAnalysis,
  onConfirm,
  isLoading = false,
}: ClarificationFormProps) {
  const [answers, setAnswers] = useState<Record<string, string | boolean>>({});

  const handleAnswerChange = (questionId: string, value: string | boolean) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
  };

  const handleSubmit = () => {
    const formattedAnswers = questions.map((q) => ({
      question_id: q.id,
      answer: answers[q.id] ?? '',
    }));
    onConfirm(formattedAnswers);
  };

  const allAnswered = questions.every((q) => answers[q.id] !== undefined);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-3xl mx-auto"
    >
      {/* Intent Summary */}
      {intentAnalysis && (
        <div className="mb-6 p-4 bg-slate-900 rounded-xl border border-slate-800">
          <h3 className="font-semibold mb-3 flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-indigo-500" />
            Understood Requirements
          </h3>
          <div className="space-y-2 text-sm">
            <p><span className="text-slate-400">Summary:</span> {intentAnalysis.summary}</p>
            {intentAnalysis.tech_stack.length > 0 && (
              <p><span className="text-slate-400">Tech Stack:</span> {intentAnalysis.tech_stack.join(', ')}</p>
            )}
            {intentAnalysis.requirements.length > 0 && (
              <div>
                <span className="text-slate-400">Requirements:</span>
                <ul className="list-disc list-inside ml-2 mt-1">
                  {intentAnalysis.requirements.slice(0, 5).map((req, i) => (
                    <li key={i}>{req}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Questions */}
      <div className="space-y-4 mb-6">
        <h3 className="font-semibold mb-3">Clarifying Questions</h3>
        {questions.map((question, index) => (
          <div key={question.id} className="p-4 bg-slate-900 rounded-xl border border-slate-800">
            <label className="block text-sm font-medium mb-2">
              <span className="text-indigo-400 mr-2">{index + 1}.</span>
              {question.question}
            </label>
            
            {question.answerType === 'boolean' ? (
              <div className="flex gap-3">
                <button
                  onClick={() => handleAnswerChange(question.id, true)}
                  className={`px-4 py-2 rounded-lg transition-colors ${
                    answers[question.id] === true
                      ? 'bg-emerald-600 text-white'
                      : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                  }`}
                >
                  Yes
                </button>
                <button
                  onClick={() => handleAnswerChange(question.id, false)}
                  className={`px-4 py-2 rounded-lg transition-colors ${
                    answers[question.id] === false
                      ? 'bg-rose-600 text-white'
                      : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                  }`}
                >
                  No
                </button>
              </div>
            ) : question.answerType === 'select' && question.options ? (
              <select
                value={(answers[question.id] as string) || ''}
                onChange={(e) => handleAnswerChange(question.id, e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 focus:outline-none focus:border-indigo-500"
              >
                <option value="">Select an option...</option>
                {question.options.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                value={(answers[question.id] as string) || ''}
                onChange={(e) => handleAnswerChange(question.id, e.target.value)}
                placeholder="Your answer..."
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 focus:outline-none focus:border-indigo-500"
              />
            )}
          </div>
        ))}
      </div>

      <Button
        onClick={handleSubmit}
        disabled={!allAnswered || isLoading}
        isLoading={isLoading}
        className="w-full"
        size="lg"
      >
        <CheckCircle className="w-5 h-5 mr-2" />
        Confirm & Generate
      </Button>
    </motion.div>
  );
}
