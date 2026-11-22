import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { auth } from "@/auth";
import { SignInCard, safeCallbackUrl } from "@/features/auth";
import { demoLogin } from "@/lib/server-env";

export const metadata: Metadata = { title: "Sign in" };

export default async function SignInPage({ searchParams }: PageProps<"/sign-in">) {
  const [session, params] = await Promise.all([auth(), searchParams]);
  const callbackUrl = safeCallbackUrl(params.callbackUrl);
  if (session?.user) redirect(callbackUrl);
  return <SignInCard callbackUrl={callbackUrl} hasDemoLogin={demoLogin() !== null} />;
}
