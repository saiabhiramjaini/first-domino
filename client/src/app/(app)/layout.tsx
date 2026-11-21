import { redirect } from "next/navigation";

import { SIGN_IN_PATH, auth } from "@/auth";
import { AppShell } from "@/components/app-shell/app-shell";
import { ApiUnavailable } from "@/components/feedback/api-unavailable";

type SignedInLayoutProps = { children: React.ReactNode };

export default async function SignedInLayout({ children }: SignedInLayoutProps) {
  const session = await auth();
  if (!session?.user) redirect(SIGN_IN_PATH);
  const user = {
    name: session.user.name ?? null,
    email: session.user.email ?? null,
    image: session.user.image ?? null,
  };
  return <AppShell user={user}>{session.apiToken ? children : <ApiUnavailable />}</AppShell>;
}
