"use client";

import { PlugZapIcon } from "lucide-react";
import { signOut } from "next-auth/react";

import { Button } from "@/components/ui/button";

import { EmptyState } from "./empty-state";

// Shown when the session has no API token (minting it failed), instead of pages that would
// wait for data forever.
export function ApiUnavailable() {
  return (
    <EmptyState
      icon={PlugZapIcon}
      title="Could not connect to First Domino"
      description="Your session could not get access to the API. Sign in again; if this keeps happening, try again in a few minutes."
      action={
        <Button
          variant="outline"
          size="sm"
          onClick={() => void signOut({ redirectTo: "/sign-in" })}
        >
          Sign in again
        </Button>
      }
    />
  );
}
