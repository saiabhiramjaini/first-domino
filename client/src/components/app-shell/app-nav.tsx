"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

import { NAV_ITEMS, isNavItemActive } from "./nav-items";

type AppNavProps = { onNavigate?: () => void };

export function AppNav({ onNavigate }: AppNavProps) {
  const pathname = usePathname();
  return (
    <nav aria-label="Main" className="flex flex-col gap-0.5">
      <span className="px-2.5 pb-1.5 text-[11px] font-medium tracking-wider text-muted-foreground uppercase">
        Workspace
      </span>
      {NAV_ITEMS.map((item) => {
        const isActive = isNavItemActive(item, pathname);
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            aria-current={isActive ? "page" : undefined}
            className={cn(
              "group relative flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm text-muted-foreground outline-none hover:bg-muted hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50",
              isActive && "bg-muted font-medium text-foreground"
            )}
          >
            {isActive && (
              <span
                className="absolute inset-y-2 -left-3 w-0.5 rounded-full bg-domino"
                aria-hidden="true"
              />
            )}
            <Icon
              className={cn(
                "size-4",
                isActive ? "text-domino" : "text-muted-foreground group-hover:text-foreground"
              )}
              aria-hidden="true"
            />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
