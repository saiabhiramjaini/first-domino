"use client";

import { ChevronRightIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { shortId } from "@/components/runs/short-id";

type Crumb = { label: string; href?: string; mono?: boolean };

// Only detail pages get a trail (a way back to their list); a list page's title says where you are.
function crumbsFor(pathname: string): Crumb[] {
  const [section, id] = pathname.split("/").filter(Boolean);
  if (!id) return [];
  switch (section) {
    case "runs":
      return [
        { label: "Runs", href: "/runs" },
        { label: shortId(id), mono: true },
      ];
    case "causes":
      return [
        { label: "Root causes", href: "/causes" },
        { label: shortId(id), mono: true },
      ];
    default:
      return [];
  }
}

export function Breadcrumbs() {
  const crumbs = crumbsFor(usePathname());
  if (crumbs.length === 0) return null;
  return (
    <nav aria-label="Breadcrumb" className="-mb-3 min-w-0">
      <ol className="flex items-center gap-1.5 text-xs">
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
