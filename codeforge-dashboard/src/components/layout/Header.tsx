import { ConnectionStatus } from '@/components/shared/ConnectionStatus';
import { MobileNav } from './MobileNav';
import { ThemeToggle } from './ThemeToggle';

export function Header() {
  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b bg-background px-4 md:px-6 lg:px-8">
      <div className="flex items-center gap-2">
        <MobileNav />
        <span className="text-base font-bold lg:hidden">CodeForge</span>
      </div>
      <div className="flex items-center gap-4">
        <ConnectionStatus />
        <ThemeToggle />
      </div>
    </header>
  );
}
