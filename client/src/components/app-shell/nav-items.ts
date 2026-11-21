import { FlameIcon, SettingsIcon, TargetIcon, type LucideIcon } from "lucide-react";

export type NavItem = { href: string; label: string; icon: LucideIcon };

export const NAV_ITEMS: readonly NavItem[] = [
  { href: "/failures", label: "Failures", icon: FlameIcon },
  { href: "/causes", label: "Root causes", icon: TargetIcon },
  { href: "/settings", label: "Settings", icon: SettingsIcon },
];

export function isNavItemActive(item: NavItem, pathname: string): boolean {
  if (pathname === item.href || pathname.startsWith(`${item.href}/`)) return true;
  return item.href === "/failures" && pathname.startsWith("/runs/");
}
