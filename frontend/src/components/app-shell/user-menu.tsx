"use client";

import { signOut } from "next-auth/react";
import { toast } from "sonner";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { reportClientError } from "@/lib/report-client-error";

import type { ShellUser } from "./shell-user";

type UserMenuProps = { user: ShellUser };

function initials(user: ShellUser): string {
  const source = user.name ?? user.email ?? "?";
  return source
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join("");
}

export function UserMenu({ user }: UserMenuProps) {
  async function handleSignOut() {
    try {
      await signOut({ redirectTo: "/" });
    } catch (error) {
      reportClientError(error, "auth.sign_out");
      toast.error("Could not sign you out. Reload the page and try again.");
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label="Open the user menu"
        className="flex w-full items-center gap-2.5 rounded-lg p-1.5 text-left outline-none hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50"
      >
        <Avatar className="size-7">
          {user.image && <AvatarImage src={user.image} alt="" />}
          <AvatarFallback>{initials(user)}</AvatarFallback>
        </Avatar>
        <span className="flex min-w-0 flex-col">
          <span className="truncate text-sm font-medium">{user.name ?? "Signed in"}</span>
          {user.email && (
            <span className="truncate text-xs text-muted-foreground">{user.email}</span>
          )}
        </span>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" side="top" className="w-56">
        <DropdownMenuGroup>
          <DropdownMenuLabel>{user.email ?? user.name ?? "Your account"}</DropdownMenuLabel>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={handleSignOut}>Sign out</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
