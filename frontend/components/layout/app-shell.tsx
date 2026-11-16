"use client";

import { Menu } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";

import { Brand } from "./brand";
import { DatasetStatus } from "./dataset-status";
import { NavLinks } from "./nav-links";

/** Fixed sidebar on wide screens; a top bar with a slide-in menu on narrow ones. */
export function AppShell({ children }: { children: React.ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="flex min-h-dvh flex-col lg:flex-row">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:bg-primary focus:px-3 focus:py-2 focus:text-primary-foreground"
      >
        Skip to content
      </a>

      <aside className="sticky top-0 hidden h-dvh w-60 shrink-0 flex-col border-r bg-sidebar lg:flex">
        <div className="flex h-14 items-center border-b px-4">
          <Brand />
        </div>
        <nav aria-label="Main" className="flex-1 overflow-y-auto py-3">
          <NavLinks />
        </nav>
        <div className="border-t p-4">
          <DatasetStatus />
        </div>
      </aside>

      <header className="sticky top-0 z-30 flex h-14 items-center justify-between gap-3 border-b bg-sidebar px-4 lg:hidden">
        <Brand />
        <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
          <SheetTrigger asChild>
            <Button variant="outline" size="icon" aria-label="Open navigation menu">
              <Menu aria-hidden />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-72 gap-0 bg-sidebar p-0">
            <SheetHeader className="h-14 justify-center border-b px-4 py-0">
              <SheetTitle asChild>
                <div>
                  <Brand onNavigate={() => setMenuOpen(false)} />
                </div>
              </SheetTitle>
              <SheetDescription className="sr-only">
                Navigate between PiScope pages
              </SheetDescription>
            </SheetHeader>
            <nav aria-label="Main" className="flex-1 overflow-y-auto py-3">
              <NavLinks onNavigate={() => setMenuOpen(false)} />
            </nav>
            <div className="border-t p-4">
              <DatasetStatus />
            </div>
          </SheetContent>
        </Sheet>
      </header>

      <main id="main" className="min-w-0 flex-1">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          {children}
        </div>
      </main>
    </div>
  );
}
