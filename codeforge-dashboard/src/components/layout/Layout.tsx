import React, { useState } from 'react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { cn } from '@/lib/utils';

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <a
        href="#main"
        className="sr-only rounded-lg bg-card px-4 py-2 text-sm font-medium shadow-overlay focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50"
      >
        Skip to content
      </a>
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />
      <div className={cn('transition-[padding] duration-200 ease-out', collapsed ? 'lg:pl-16' : 'lg:pl-60')}>
        <Header />
        <main id="main" className="mx-auto max-w-7xl px-4 py-8 md:px-6 lg:px-8">
          {children}
        </main>
      </div>
    </div>
  );
}
