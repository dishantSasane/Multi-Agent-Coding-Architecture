import { Bolt, Clock, Settings, ChevronsLeft, ChevronsRight } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { cn } from '@/lib/utils';

const navItems = [
  { icon: Bolt, label: 'New Query', path: '/' },
  { icon: Clock, label: 'History', path: '/history' },
  { icon: Settings, label: 'Settings', path: '/settings' },
];

interface NavLinksProps {
  collapsed?: boolean;
  onNavigate?: () => void;
}

/** Shared by the desktop sidebar and the mobile drawer. */
export function NavLinks({ collapsed = false, onNavigate }: NavLinksProps) {
  return (
    <ul className="space-y-2">
      {navItems.map(({ icon: Icon, label, path }) => (
        <li key={path}>
          <NavLink
            to={path}
            end
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                'flex h-12 items-center gap-4 rounded-lg text-sm font-medium transition-colors duration-150 ease-out',
                collapsed ? 'justify-center' : 'px-4',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-secondary hover:text-foreground active:bg-secondary/70'
              )
            }
          >
            <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
            <span className={cn(collapsed && 'sr-only')}>{label}</span>
          </NavLink>
        </li>
      ))}
    </ul>
  );
}

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  return (
    <aside
      className={cn(
        'fixed inset-y-0 left-0 z-30 hidden flex-col border-r bg-card transition-[width] duration-200 ease-out lg:flex',
        collapsed ? 'w-16' : 'w-60'
      )}
    >
      <div className={cn('flex h-16 items-center border-b', collapsed ? 'justify-center' : 'justify-between px-4')}>
        {!collapsed && (
          <span className="flex items-center gap-2 text-base font-bold">
            <Bolt className="h-5 w-5 text-accent" aria-hidden="true" />
            CodeForge
          </span>
        )}
        <button
          type="button"
          onClick={onToggle}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-expanded={!collapsed}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors duration-150 ease-out hover:bg-secondary hover:text-foreground active:bg-secondary/70"
        >
          {collapsed ? (
            <ChevronsRight className="h-4 w-4" aria-hidden="true" />
          ) : (
            <ChevronsLeft className="h-4 w-4" aria-hidden="true" />
          )}
        </button>
      </div>
      <nav aria-label="Main" className="flex-1 p-2">
        <NavLinks collapsed={collapsed} />
      </nav>
    </aside>
  );
}
