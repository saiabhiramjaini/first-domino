"use client";

import { ChevronRightIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { shortId } from "@/components/runs/short-id";

type Crumb = { label: string; href?: string; mono?: boolean };

function crumbsFor(pathname: string): Crumb[] {
  const [section, id] = pathname.split("/").filter(Boolean);
  switch (section) {
    case "runs":
      return id
        ? [
            { label: "Runs", href: "/runs" },
            { label: shortId(id), mono: true },
          ]
        : [{ label: "Runs" }];
    case "causes":
      return id
        ? [
            { label: "Root causes", href: "/causes" },
            { label: shortId(id), mono: true },
          ]
        : [{ label: "Root causes" }];
    case "settings":
      return [{ label: "Settings" }, { label: "Connect your agent" }];
    default:
      return [{ label: "Failures" }];
  }
}

export function Breadcrumbs() {
  const crumbs = crumbsFor(usePathname());
  return (
    <nav aria-label="Breadcrumb" className="min-w-0">
      <ol className="flex items-center gap-1.5 text-sm">
        {crumbs.map((crumb, index) => {
          const isLast = index === crumbs.length - 1;
          return (
            <li key={`${crumb.label}-${index}`} className="flex min-w-0 items-center gap-1.5">
              {index > 0 && (
                <ChevronRightIcon className="size-3.5 text-muted-foreground" aria-hidden="true" />
              )}
              {crumb.href && !isLast ? (
                <Link
                  href={crumb.href}
                  className="text-muted-foreground outline-none hover:text-foreground focus-visible:underline"
                >
                  {crumb.label}
                </Link>
              ) : (
                <span
                  aria-current={isLast ? "page" : undefined}
                  className={crumb.mono ? "truncate font-mono text-xs" : "truncate font-medium"}
                >
                  {crumb.label}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
