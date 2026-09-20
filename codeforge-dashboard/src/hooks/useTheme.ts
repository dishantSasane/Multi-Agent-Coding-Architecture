import { useCallback, useEffect, useState } from 'react';

export type Theme = 'light' | 'dark' | 'system';

const KEY = 'codeforge-theme'; // also read by the inline script in index.html
const ORDER: Theme[] = ['light', 'dark', 'system'];
const media = () => window.matchMedia('(prefers-color-scheme: dark)');

const read = (): Theme => {
  try {
    const v = localStorage.getItem(KEY);
    return v === 'light' || v === 'dark' ? v : 'system';
  } catch {
    return 'system';
  }
};

function apply(theme: Theme) {
  const dark = theme === 'dark' || (theme === 'system' && media().matches);
  document.documentElement.classList.toggle('dark', dark);
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute('content', dark ? '#161512' : '#F5F1EA');
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(read);

  useEffect(() => {
    apply(theme);
    if (theme !== 'system') return;
    const m = media();
    const onChange = () => apply('system'); // follow the OS while in system mode
    m.addEventListener('change', onChange);
    return () => m.removeEventListener('change', onChange);
  }, [theme]);

  const cycle = useCallback(() => {
    const next = ORDER[(ORDER.indexOf(theme) + 1) % ORDER.length];
    try {
      localStorage.setItem(KEY, next);
    } catch {
      /* storage blocked: the choice still applies for this session */
    }
    setTheme(next);
  }, [theme]);

  return { theme, cycle };
}
