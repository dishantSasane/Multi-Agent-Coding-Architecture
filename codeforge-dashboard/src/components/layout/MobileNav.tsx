import { useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { Bolt, Menu, X } from 'lucide-react';
import { NavLinks } from './Sidebar';

/** Drawer navigation below the lg breakpoint. Radix handles Esc, focus trap and focus return. */
export function MobileNav() {
  const [open, setOpen] = useState(false);

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <button
          type="button"
          aria-label="Open menu"
          className="flex h-10 w-10 items-center justify-center rounded-lg text-foreground transition-colors duration-150 ease-out hover:bg-secondary active:bg-secondary/70 lg:hidden"
        >
          <Menu className="h-5 w-5" aria-hidden="true" />
        </button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-background/80" />
        <Dialog.Content className="fixed inset-y-0 left-0 z-50 w-60 max-w-full bg-card shadow-overlay focus:outline-none">
          <div className="flex h-16 items-center justify-between border-b px-4">
            <Dialog.Title className="flex items-center gap-2 text-base font-bold">
              <Bolt className="h-5 w-5 text-accent" aria-hidden="true" />
              CodeForge
            </Dialog.Title>
            <Dialog.Close asChild>
              <button
                type="button"
                aria-label="Close menu"
                className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors duration-150 ease-out hover:bg-secondary hover:text-foreground active:bg-secondary/70"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </Dialog.Close>
          </div>
          <Dialog.Description className="sr-only">Site navigation</Dialog.Description>
          <nav aria-label="Main" className="p-2">
            <NavLinks onNavigate={() => setOpen(false)} />
          </nav>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
