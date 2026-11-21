import Link from "next/link";

import { BrandName } from "@/components/brand/brand-name";

import { GoogleSignInButton } from "./google-sign-in-button";

type SignInCardProps = { callbackUrl: string };

export function SignInCard({ callbackUrl }: SignInCardProps) {
  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-4">
      <div className="relative flex w-full max-w-sm flex-col items-center gap-8">
        <Link
          href="/"
          aria-label="First Domino home"
          className="rounded-md outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          <BrandName />
        </Link>
        <div className="flex w-full flex-col gap-6 rounded-xl border bg-card/90 p-6 backdrop-blur">
          <div className="flex flex-col gap-1.5 text-center">
            <h1 className="text-xl font-semibold tracking-tight">Sign in to First Domino</h1>
            <p className="text-sm text-pretty text-muted-foreground">
              Use your Google account. Your project is created on first sign-in.
            </p>
          </div>
          <GoogleSignInButton callbackUrl={callbackUrl} />
          <p className="text-center text-xs text-muted-foreground">
            We only read your name, email and picture from Google.
          </p>
        </div>
        <Link href="/" className="text-sm text-muted-foreground hover:text-foreground">
          Back to the home page
        </Link>
      </div>
    </div>
  );
}
