import { auth } from "@/auth";
import { LandingPage } from "@/features/landing";

export default async function HomePage() {
  const session = await auth();
  return <LandingPage isSignedIn={Boolean(session?.user)} />;
}
