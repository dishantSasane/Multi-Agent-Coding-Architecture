import { Monitor, Moon, Sun } from 'lucide-react';
import { useTheme } from '@/hooks/useTheme';

const ICONS = { light: Sun, dark: Moon, system: Monitor };
const NEXT = { light: 'dark', dark: 'system', system: 'light' } as const;

/** Cycles light -> dark -> system. The label states the current mode and what a click does. */
export function ThemeToggle() {
  const { theme, cycle } = useTheme();
  const Icon = ICONS[theme];

  return (
    <button
      type="button"
      onClick={cycle}
      aria-label={`Theme: ${theme}. Switch to ${NEXT[theme]}`}
      title={`Theme: ${theme}`}
      className="flex h-10 w-10 items-center justify-center rounded-lg text-muted-foreground transition-colors duration-150 ease-out hover:bg-secondary hover:text-foreground active:bg-secondary/70"
    >
      <Icon className="h-5 w-5" aria-hidden="true" />
    </button>
  );
}
