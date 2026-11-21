"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

import { NAV_ITEMS, isNavItemActive } from "./nav-items";

type AppNavProps = { onNavigate?: () => void };

export function AppNav({ onNavigate }: AppNavProps) {
  const pathname = usePathname();
  return (
    <nav aria-label="Main" className="flex flex-col gap-px">
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
              "flex h-8 items-center gap-2.5 rounded-md px-2 text-sm text-muted-foreground outline-none hover:bg-muted/60 hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50",
              isActive && "bg-muted text-foreground"
            )}
          >
            <Icon className="size-4" aria-hidden="true" />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
