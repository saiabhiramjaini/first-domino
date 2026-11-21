import { ListIcon, Layers3Icon, SettingsIcon, type LucideIcon } from "lucide-react";

export type NavItem = { href: string; label: string; icon: LucideIcon };

// Failures are the Runs list filtered to failed runs, so they have no item of their own.
export const NAV_ITEMS: readonly NavItem[] = [
  { href: "/runs", label: "Runs", icon: ListIcon },
  { href: "/causes", label: "Root causes", icon: Layers3Icon },
  { href: "/settings", label: "Settings", icon: SettingsIcon },
];

export function isNavItemActive(item: NavItem, pathname: string): boolean {
  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}
