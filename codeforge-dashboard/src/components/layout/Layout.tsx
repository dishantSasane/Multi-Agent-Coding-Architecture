import React, { useState, useEffect } from 'react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { testConnection } from '@/lib/api';
import { useAppStore } from '@/store/appStore';

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const setConnectionStatus = useAppStore((s) => s.setConnectionStatus);

  // Health-check loop: resolve "Connecting..." on mount, re-check every 30 s
  useEffect(() => {
    let cancelled = false;

    const check = async () => {
      const ok = await testConnection();
      if (!cancelled) {
        setConnectionStatus(ok ? 'online' : 'offline');
      }
    };

    check();
    const id = setInterval(check, 30_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [setConnectionStatus]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      />

      <div
        className="transition-all duration-200"
        style={{ marginLeft: sidebarCollapsed ? 64 : 240 }}
      >
        <Header />
        <main className="p-6">{children}</main>
      </div>
    </div>
  );
}
