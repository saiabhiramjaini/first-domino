import { PlugIcon } from "lucide-react";
import Link from "next/link";

import { BrandName } from "@/components/brand/brand-name";
import { buttonVariants } from "@/components/ui/button";

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
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r bg-sidebar md:flex">
        <div className="flex h-14 items-center border-b px-4">
          <Link
            href="/failures"
            aria-label="First Domino home"
            className="rounded-md outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
          >
            <BrandName />
          </Link>
        </div>
        <div className="flex flex-1 flex-col gap-5 overflow-y-auto p-3">
          <ProjectName />
          <AppNav />
        </div>
        <div className="flex flex-col gap-1 border-t p-3">
          <Link
            href="/settings"
            className="flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm text-muted-foreground outline-none hover:bg-muted hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50"
          >
            <PlugIcon className="size-4" aria-hidden="true" />
            Connect your agent
          </Link>
          <UserMenu user={user} />
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-14 items-center justify-between gap-3 border-b bg-background/80 px-4 backdrop-blur-md md:px-8">
          <div className="flex min-w-0 items-center gap-2">
            <div className="md:hidden">
              <MobileNav />
            </div>
            <Breadcrumbs />
          </div>
          <Link
            href="/settings"
            className={buttonVariants({
              variant: "outline",
              size: "sm",
              className: "hidden sm:inline-flex",
            })}
          >
            <PlugIcon aria-hidden="true" />
            Connect agent
          </Link>
        </header>
        <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-8 px-4 py-8 md:px-8">
          {children}
        </main>
      </div>
    </div>
  );
}
