import React from 'react';
import { Bolt } from 'lucide-react';
import { ConnectionStatus } from '@/components/shared/ConnectionStatus';

export function Header() {
  return (
    <header className="h-16 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-6">
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-bold flex items-center gap-2">
          <Bolt className="w-6 h-6 text-indigo-500" />
          CodeForge
        </h1>
      </div>
      
      <div className="flex items-center gap-4">
        <ConnectionStatus />
      </div>
    </header>
  );
}
