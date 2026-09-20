import { Wifi, WifiOff } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useHealth } from '@/hooks/useTask';

export function ConnectionStatus() {
  const { data, isPending } = useHealth();
  const state = isPending ? 'checking' : data ? 'online' : 'offline';

  const config = {
    online: { Icon: Wifi, label: 'Backend online', color: 'text-success' },
    offline: { Icon: WifiOff, label: 'Backend offline', color: 'text-destructive' },
    checking: { Icon: Wifi, label: 'Checking backend', color: 'text-muted-foreground' },
  }[state];

  return (
    <div role="status" className={cn('flex items-center gap-2 text-sm font-medium', config.color)}>
      <config.Icon className="h-4 w-4" aria-hidden="true" />
      <span className="hidden sm:inline">{config.label}</span>
    </div>
  );
}
