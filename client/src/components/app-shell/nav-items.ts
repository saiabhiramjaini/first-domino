import { ActivityIcon, FlameIcon, SettingsIcon, TargetIcon, type LucideIcon } from "lucide-react";

export type NavItem = { href: string; label: string; icon: LucideIcon };

export const NAV_ITEMS: readonly NavItem[] = [
  { href: "/runs", label: "Runs", icon: ActivityIcon },
  { href: "/failures", label: "Failures", icon: FlameIcon },
  { href: "/causes", label: "Root causes", icon: TargetIcon },
  { href: "/settings", label: "Settings", icon: SettingsIcon },
];

export function isNavItemActive(item: NavItem, pathname: string): boolean {
  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}
