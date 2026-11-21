import Link from "next/link";

import { BrandName } from "@/components/brand/brand-name";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

import { GoogleSignInButton } from "./google-sign-in-button";

type SignInCardProps = { callbackUrl: string };

export function SignInCard({ callbackUrl }: SignInCardProps) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-8 px-4">
      <Link href="/" aria-label="First Domino home">
        <BrandName />
      </Link>
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Sign in</CardTitle>
          <CardDescription>
            Use your Google account. Your project is created on first sign-in.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <GoogleSignInButton callbackUrl={callbackUrl} />
        </CardContent>
      </Card>
    </div>
  );
}
