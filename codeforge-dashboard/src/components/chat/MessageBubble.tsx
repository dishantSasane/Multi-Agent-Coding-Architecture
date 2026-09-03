import React from 'react';
import { motion } from 'framer-motion';
import { User, Bot } from 'lucide-react';
import { cn } from '@/lib/utils';

interface MessageBubbleProps {
  message: string;
  isUser: boolean;
  timestamp?: string;
}

export function MessageBubble({ message, isUser, timestamp }: MessageBubbleProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        'flex gap-3 max-w-3xl',
        isUser ? 'ml-auto flex-row-reverse' : ''
      )}
    >
      <div
        className={cn(
          'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
          isUser ? 'bg-indigo-600' : 'bg-slate-700'
        )}
      >
        {isUser ? (
          <User className="w-5 h-5" />
        ) : (
          <Bot className="w-5 h-5" />
        )}
      </div>
      
      <div
        className={cn(
          'px-4 py-3 rounded-2xl max-w-[80%]',
          isUser
            ? 'bg-indigo-600 text-white rounded-br-sm'
            : 'bg-slate-800 text-slate-100 rounded-bl-sm'
        )}
      >
        <p className="whitespace-pre-wrap leading-relaxed">{message}</p>
        
        {timestamp && (
          <span className={cn('text-xs mt-2 block', isUser ? 'text-indigo-200' : 'text-slate-400')}>
            {timestamp}
          </span>
        )}
      </div>
    </motion.div>
  );
}
