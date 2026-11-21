import Link from "next/link";

import { BrandName } from "@/components/brand/brand-name";

import { AppNav } from "./app-nav";
import { MobileNav } from "./mobile-nav";
import { ProjectName } from "./project-name";
import type { ShellUser } from "./shell-user";
import { UserMenu } from "./user-menu";

type AppShellProps = { user: ShellUser; children: React.ReactNode };

export function AppShell({ user, children }: AppShellProps) {
  return (
    <div className="flex min-h-screen w-full">
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col gap-6 border-r bg-sidebar p-4 md:flex">
        <Link href="/failures" aria-label="First Domino home" className="px-1.5">
          <BrandName />
        </Link>
        <ProjectName />
        <div className="flex-1">
          <AppNav />
        </div>
        <UserMenu user={user} />
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-10 flex items-center justify-between gap-2 border-b bg-background/95 px-4 py-2 backdrop-blur md:hidden">
          <MobileNav />
          <Link href="/failures" aria-label="First Domino home">
            <BrandName />
          </Link>
          <div className="w-8" aria-hidden="true" />
        </header>
        <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-4 py-6 md:px-8 md:py-8">
          {children}
        </main>
      </div>
    </div>
  );
}
