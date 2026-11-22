"use client";

import { signIn } from "next-auth/react";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { reportClientError } from "@/lib/report-client-error";

type DemoSignInFormProps = { callbackUrl: string };

/** Email and password for the shared test account, for reviewers who cannot use Google. */
export function DemoSignInForm({ callbackUrl }: DemoSignInFormProps) {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setIsPending(true);
    setError(null);
    try {
      const result = await signIn("demo", {
        email: String(form.get("email") ?? ""),
        password: String(form.get("password") ?? ""),
        redirect: false,
      });
      if (result?.error) {
        setError("That email and password do not match the test login.");
        setIsPending(false);
        return;
      }
      window.location.assign(callbackUrl);
    } catch (err) {
      reportClientError(err, "auth.demo_sign_in");
      setError("Could not sign in. Check your connection and try again.");
      setIsPending(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3" aria-label="Test login">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="demo-email">Email</Label>
        <Input id="demo-email" name="email" type="email" autoComplete="username" required />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="demo-password">Password</Label>
        <Input
          id="demo-password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
        />
      </div>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      <Button type="submit" variant="outline" size="lg" className="w-full" disabled={isPending}>
        {isPending ? "Signing in..." : "Sign in with the test login"}
      </Button>
    </form>
  );
}
