import Link from "next/link";

import { BrandName } from "@/components/brand/brand-name";

import { AppNav } from "./app-nav";
import { Breadcrumbs } from "./breadcrumbs";
import { MobileNav } from "./mobile-nav";
import { ProjectName } from "./project-name";
import type { ShellUser } from "./shell-user";
import { UserMenu } from "./user-menu";

type AppShellProps = { user: ShellUser; children: React.ReactNode };

export function AppShell({ user, children }: AppShellProps) {
  return (
    <div className="flex min-h-screen w-full bg-background">
      <aside className="sticky top-0 hidden h-screen w-56 shrink-0 flex-col border-r border-sidebar-border md:flex">
        <div className="flex h-12 items-center px-4">
          <Link
            href="/runs"
            aria-label="First Domino home"
            className="rounded-md outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
          >
            <BrandName />
          </Link>
        </div>
        <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-2 py-3">
          <ProjectName />
          <AppNav />
        </div>
        <div className="border-t border-sidebar-border p-2">
          <UserMenu user={user} />
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        {/* On a phone the sidebar is hidden, so this bar holds the menu button. */}
        <header className="sticky top-0 z-20 flex h-12 items-center gap-2 border-b bg-background/90 px-4 backdrop-blur-sm md:hidden">
          <MobileNav />
          <BrandName />
        </header>
        <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-6 px-4 py-6 md:px-8 md:py-8">
          <Breadcrumbs />
          {children}
        </main>
      </div>
    </div>
  );
}
