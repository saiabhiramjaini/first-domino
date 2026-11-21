import Link from "next/link";

import { BrandName } from "@/components/brand/brand-name";
import { buttonVariants } from "@/components/ui/button";

import { BisectDemo } from "./bisect-demo";
import { DominoRow } from "./domino-row";

const STEPS = [
  {
    title: "Replay from save points",
    body: "Every step of a recorded run is a save point. We keep steps 1 to m and let your own agent run the rest, on your side.",
  },
  {
    title: "Bisect to the first doomed step",
    body: "A binary search finds the first save point from which every replay fails. That step is the first domino.",
  },
  {
    title: "Prove it with a fix",
    body: "We rewrite that one step and replay. When the run flips from failed to passed, the cause is proven, not guessed.",
  },
] as const;

type LandingPageProps = { isSignedIn: boolean };

export function LandingPage({ isSignedIn }: LandingPageProps) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="mx-auto flex w-full max-w-5xl items-center justify-between px-4 py-4">
        <BrandName />
        <Link
          href={isSignedIn ? "/failures" : "/sign-in"}
          className={buttonVariants({ variant: "outline" })}
        >
          {isSignedIn ? "Open the app" : "Sign in"}
        </Link>
      </header>

      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-16 px-4 py-12 sm:py-20">
        <section className="flex flex-col items-center gap-6 text-center">
          <p className="rounded-full border px-3 py-1 text-xs text-muted-foreground">
            Built for teams like Equal AI that run AI call assistants
          </p>
          <h1 className="max-w-3xl text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
            Find the step where your agent&apos;s run was lost.
          </h1>
          <p className="max-w-2xl text-lg text-pretty text-muted-foreground">
            Your call assistant booked the callback for the wrong day. First Domino re-runs the
            failed call from its own save points, finds the first step that doomed it, then proves
            it by fixing that step and replaying.
          </p>
          <Link
            href={isSignedIn ? "/failures" : "/sign-in"}
            className={buttonVariants({ size: "lg" })}
          >
            {isSignedIn ? "Open your failures" : "Sign in with Google"}
          </Link>
        </section>

        <section aria-labelledby="idea-title" className="flex flex-col items-center gap-6">
          <h2 id="idea-title" className="sr-only">
            The first domino
          </h2>
          <DominoRow />
        </section>

        <section aria-labelledby="how-title" className="flex flex-col gap-6">
          <div className="flex flex-col gap-2 text-center">
            <h2 id="how-title" className="text-2xl font-semibold tracking-tight">
              How it works
            </h2>
            <p className="text-sm text-muted-foreground">
              A 12-step call, narrowed to one step in four checks and proven with one fix.
            </p>
          </div>
          <BisectDemo />
          <div className="grid gap-4 sm:grid-cols-3">
            {STEPS.map((step, position) => (
              <article
                key={step.title}
                className="flex flex-col gap-2 rounded-xl border bg-card p-5"
              >
                <span className="text-sm font-medium text-domino">{position + 1}</span>
                <h3 className="font-medium">{step.title}</h3>
                <p className="text-sm text-muted-foreground">{step.body}</p>
              </article>
            ))}
          </div>
        </section>
      </main>

      <footer className="mx-auto w-full max-w-5xl px-4 py-6 text-sm text-muted-foreground">
        Built for Builders 2026.
      </footer>
    </div>
  );
}
