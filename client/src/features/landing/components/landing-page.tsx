import { ArrowRightIcon, KeyRoundIcon, ListChecksIcon, ShieldCheckIcon } from "lucide-react";
import Link from "next/link";

import { BrandName } from "@/components/brand/brand-name";
import { buttonVariants } from "@/components/ui/button";

import { BisectDemo } from "./bisect-demo";
import { ProductPreview } from "./product-preview";

const STEPS = [
  {
    title: "Replay from save points",
    body: "Every step of a recorded run is a save point. We keep steps 1 to m exactly as recorded and let your own agent run the rest, on your side.",
  },
  {
    title: "Bisect to the first doomed step",
    body: "A binary search finds the first save point from which every replay fails. That step is the first domino, found in about log₂(n) checks.",
  },
  {
    title: "Prove it with a fix",
    body: "We rewrite that one step and replay. When the run flips from failed to passed, the cause is proven, not guessed.",
  },
] as const;

const PRINCIPLES = [
  {
    icon: ShieldCheckIcon,
    title: "Proven, not guessed",
    body: "A trace-reading model names a step. First Domino replays to show the run can still pass before it and always fails after it.",
  },
  {
    icon: KeyRoundIcon,
    title: "Your code stays with you",
    body: "Replays run in a worker next to your agent that only connects outward. Your tools, data and secrets never leave your machines.",
  },
  {
    icon: ListChecksIcon,
    title: "From incident to test",
    body: "Failures are grouped into root causes. Export a cause's runs as test cases and keep the bug from coming back.",
  },
] as const;

const SDK_SNIPPET = `import first_domino as fd

@fd.entrypoint("support-bot", check=is_good_answer)
def answer(question: str) -> str:
    ...  # your agent, unchanged

# worker.py, next to your agent
fd.serve()  # replays on your side, on request`;

type LandingPageProps = { isSignedIn: boolean };

export function LandingPage({ isSignedIn }: LandingPageProps) {
  const appHref = isSignedIn ? "/runs" : "/sign-in";
  return (
    <div className="relative flex min-h-screen flex-col overflow-x-clip">
      <header className="sticky top-0 z-30 bg-background/70 backdrop-blur-md">
        <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-4 sm:px-6">
          <Link
            href="/"
            aria-label="First Domino home"
            className="rounded-md outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
          >
            <BrandName />
          </Link>
          <nav
            aria-label="Sections"
            className="hidden items-center gap-6 text-sm text-muted-foreground md:flex"
          >
            <a href="#how" className="hover:text-foreground">
              How it works
            </a>
            <a href="#why" className="hover:text-foreground">
              Why First Domino
            </a>
            <a href="#sdk" className="hover:text-foreground">
              SDK
            </a>
          </nav>
          <Link
            href={appHref}
            className={buttonVariants({ variant: isSignedIn ? "brand" : "outline", size: "sm" })}
          >
            {isSignedIn ? "Open the app" : "Sign in"}
          </Link>
        </div>
      </header>

      <main className="relative flex flex-1 flex-col">
        <section className="mx-auto flex w-full max-w-6xl flex-col items-center gap-8 px-4 pt-20 pb-16 text-center sm:px-6 sm:pt-28">
          <span className="inline-flex items-center gap-2 rounded-full border bg-card/60 px-3 py-1 text-xs text-muted-foreground">
            <span className="size-1.5 rounded-full bg-domino" aria-hidden="true" />
            Root causes for failed AI agent runs
          </span>
          <h1 className="max-w-4xl text-4xl font-semibold tracking-[-0.035em] text-balance sm:text-6xl">
            Find the step where your agent&apos;s run was lost.
          </h1>
          <p className="max-w-2xl text-lg text-pretty text-muted-foreground">
            First Domino replays a failed run from its own save points, finds the first step that
            doomed it, then proves it by fixing that one step and replaying.
          </p>
          <div className="flex flex-col items-center gap-3 sm:flex-row">
            <Link href={appHref} className={buttonVariants({ variant: "brand", size: "lg" })}>
              {isSignedIn ? "Open the app" : "Get started free"}
              <ArrowRightIcon data-icon="inline-end" aria-hidden="true" />
            </Link>
            <a href="#how" className={buttonVariants({ variant: "outline", size: "lg" })}>
              See how it works
            </a>
          </div>
          <div className="mt-8 w-full max-w-4xl">
            <ProductPreview />
          </div>
        </section>

        <section id="how" aria-labelledby="how-title" className="scroll-mt-20 border-t">
          <div className="mx-auto flex w-full max-w-6xl flex-col gap-10 px-4 py-20 sm:px-6">
            <div className="flex max-w-2xl flex-col gap-3">
              <span className="font-mono text-xs text-muted-foreground">How it works</span>
              <h2 id="how-title" className="text-3xl font-semibold tracking-tight text-balance">
                A 12-step call, narrowed to one step in four checks.
              </h2>
              <p className="text-pretty text-muted-foreground">
                Step through a real search. Outlined steps are still in range, filled grey ones are
                ruled out, and violet is the first domino.
              </p>
            </div>
            <div className="grid items-start gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,22rem)]">
              <BisectDemo />
              <ol className="flex flex-col gap-6">
                {STEPS.map((step, position) => (
                  <li key={step.title} className="flex gap-4">
                    <span className="flex size-7 shrink-0 items-center justify-center rounded-full border font-mono text-xs text-muted-foreground">
                      {position + 1}
                    </span>
                    <div className="flex flex-col gap-1">
                      <h3 className="font-medium">{step.title}</h3>
                      <p className="text-sm text-pretty text-muted-foreground">{step.body}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </section>

        <section id="why" aria-labelledby="why-title" className="scroll-mt-20 border-t">
          <div className="mx-auto flex w-full max-w-6xl flex-col gap-10 px-4 py-20 sm:px-6">
            <div className="flex max-w-2xl flex-col gap-3">
              <span className="font-mono text-xs text-muted-foreground">Why First Domino</span>
              <h2 id="why-title" className="text-3xl font-semibold tracking-tight text-balance">
                Other tools tell you a run failed. This one tells you why, with proof.
              </h2>
            </div>
            <div className="grid gap-px overflow-hidden rounded-lg border bg-border md:grid-cols-3">
              {PRINCIPLES.map((item) => (
                <article key={item.title} className="flex flex-col gap-3 bg-card p-6">
                  <item.icon className="size-5 text-muted-foreground" aria-hidden="true" />
                  <h3 className="font-medium">{item.title}</h3>
                  <p className="text-sm text-pretty text-muted-foreground">{item.body}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="sdk" aria-labelledby="sdk-title" className="scroll-mt-20 border-t">
          <div className="mx-auto grid w-full max-w-6xl items-center gap-10 px-4 py-20 sm:px-6 lg:grid-cols-2">
            <div className="flex flex-col gap-4">
              <span className="font-mono text-xs text-muted-foreground">Python SDK</span>
              <h2 id="sdk-title" className="text-3xl font-semibold tracking-tight text-balance">
                Add two lines. Run one worker. Done.
              </h2>
              <p className="text-pretty text-muted-foreground">
                Mark the function that runs your agent, and every model call inside it is recorded
                live. A failed run is diagnosed on its own, and the worker replays it next to your
                agent when First Domino asks.
              </p>
              <ul className="flex flex-col gap-2 text-sm text-muted-foreground">
                <li>Works with OpenAI, Anthropic, LangChain and the OpenAI Agents SDK</li>
                <li>Recording never raises into your agent</li>
                <li>Your own check decides what passing means</li>
              </ul>
            </div>
            <div className="min-w-0 overflow-hidden rounded-lg border bg-card">
              <div className="flex items-center justify-between border-b px-4 py-2.5">
                <span className="font-mono text-xs text-muted-foreground">agent.py</span>
                <span className="font-mono text-xs text-muted-foreground">python</span>
              </div>
              <pre className="overflow-x-auto p-4 font-mono text-xs leading-relaxed sm:text-sm">
                <code>{SDK_SNIPPET}</code>
              </pre>
            </div>
          </div>
        </section>

        <section className="border-t">
          <div className="mx-auto flex w-full max-w-6xl flex-col items-center gap-6 px-4 py-24 text-center sm:px-6">
            <h2 className="max-w-2xl text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
              Stop guessing which step broke your agent.
            </h2>
            <Link href={appHref} className={buttonVariants({ variant: "brand", size: "lg" })}>
              {isSignedIn ? "Open the app" : "Get started free"}
              <ArrowRightIcon data-icon="inline-end" aria-hidden="true" />
            </Link>
          </div>
        </section>
      </main>

      <footer className="border-t">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-2 px-4 py-8 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <BrandName />
          <span>Proven root causes for failed AI agent runs.</span>
        </div>
      </footer>
    </div>
  );
}
