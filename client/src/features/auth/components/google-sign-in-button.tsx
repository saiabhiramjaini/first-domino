"use client";

import { signIn } from "next-auth/react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { reportClientError } from "@/lib/report-client-error";

type GoogleSignInButtonProps = { callbackUrl: string };

export function GoogleSignInButton({ callbackUrl }: GoogleSignInButtonProps) {
  const [isPending, setIsPending] = useState(false);

  async function handleClick() {
    setIsPending(true);
    try {
      await signIn("google", { redirectTo: callbackUrl });
    } catch (error) {
      reportClientError(error, "auth.sign_in");
      toast.error("Could not reach Google. Check your connection and try again.");
      setIsPending(false);
    }
  }

  return (
    <Button size="lg" className="w-full" onClick={handleClick} disabled={isPending}>
      {isPending ? "Opening Google..." : "Continue with Google"}
    </Button>
  );
}
