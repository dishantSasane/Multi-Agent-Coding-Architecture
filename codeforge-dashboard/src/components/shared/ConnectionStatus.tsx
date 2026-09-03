import React from 'react';
import { Wifi, WifiOff, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAppStore } from '@/store/appStore';

export function ConnectionStatus() {
  const connectionStatus = useAppStore((state) => state.connectionStatus);

  const statusConfig = {
    online: {
      icon: Wifi,
      label: 'Online',
      color: 'text-emerald-500',
      bg: 'bg-emerald-500/10',
      pulse: true,
    },
    offline: {
      icon: WifiOff,
      label: 'Offline',
      color: 'text-rose-500',
      bg: 'bg-rose-500/10',
      pulse: false,
    },
    checking: {
      icon: Loader2,
      label: 'Connecting...',
      color: 'text-amber-500',
      bg: 'bg-amber-500/10',
      pulse: false,
    },
  };

  const config = statusConfig[connectionStatus];
  const Icon = config.icon;

  return (
    <div
      className={cn(
        'flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-all',
        config.bg,
        config.color
      )}
    >
      <Icon className={cn('w-4 h-4', config.pulse && 'animate-pulse')} />
      <span>{config.label}</span>
    </div>
  );
}
