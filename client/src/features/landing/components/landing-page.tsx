import { CheckIcon, KeyRoundIcon, ListChecksIcon, ShieldCheckIcon, XIcon } from "lucide-react";
import Link from "next/link";

import { BrandName } from "@/components/brand/brand-name";
import { buttonVariants } from "@/components/ui/button";

import { BisectStory } from "./bisect-story";
import { Closing } from "./closing";
import { Film } from "./film";
import { Hero } from "./hero";
import { Reveal } from "./reveal";
import { SmoothScroll } from "./smooth-scroll";
import { SpotlightCard } from "./spotlight-card";

// Fair to the tools named in the hero: they record and score runs well. What they do not do is
// replay a run to find the step that broke it, and prove the fix.
const TRACING = [
  { ok: true, text: "Records every model call and tool result" },
  { ok: true, text: "Scores the run with a judge model" },
  { ok: false, text: "Names a likely cause: an AI guess" },
  { ok: false, text: "Never replays the run to check it" },
  { ok: false, text: "Leaves you to find out if the fix works" },
] as const;

const FIRST_DOMINO = [
  "Records every step with two lines of Python",
  "Scores the run with your own check",
  "Finds the exact step by replaying from save points",
  "Proves it: fixes that step, replays, 3 of 3 pass",
  "Groups failures by proven cause and emails you the fix",
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
    body: "Failures are grouped into root causes, and the first time a new one appears you get an email with the fix. Export a cause's runs as tests.",
  },
] as const;

type Tone = "kw" | "deco" | "str" | "fn" | "comment";
const TONE: Record<Tone, string> = {
  kw: "#d38cf0",
  deco: "#e5c07b",
  str: "#9ad186",
  fn: "#6ea8fe",
  comment: "#6a6a75",
};
const SDK_LINES: { hot?: boolean; spans: { text: string; tone?: Tone }[] }[] = [
  {
    hot: true,
    spans: [
      { text: "import ", tone: "kw" },
      { text: "first_domino " },
      { text: "as ", tone: "kw" },
      { text: "fd" },
    ],
  },
  { spans: [] },
  {
    hot: true,
    spans: [
      { text: "@fd.entrypoint", tone: "deco" },
      { text: "(" },
      { text: '"support-bot"', tone: "str" },
      { text: ", check=is_good_answer)" },
    ],
  },
  {
    spans: [
      { text: "def ", tone: "kw" },
      { text: "answer", tone: "fn" },
      { text: "(question: str) -> str:" },
    ],
  },
  { spans: [{ text: "    ...  " }, { text: "# your agent, unchanged", tone: "comment" }] },
  { spans: [] },
  { spans: [{ text: "# worker.py, next to your agent", tone: "comment" }] },
  {
    spans: [
      { text: "fd.serve()  " },
      { text: "# replays on your side, on request", tone: "comment" },
    ],
  },
];

function SectionHeading({
  id,
  eyebrow,
  title,
  body,
}: {
  id: string;
  eyebrow: string;
  title: string;
  body?: string;
}) {
  return (
    <Reveal className="flex max-w-3xl flex-col gap-4">
      <span className="font-mono text-xs text-muted-foreground">{eyebrow}</span>
      <h2
        id={id}
        className="text-4xl font-bold text-balance sm:text-5xl"
        style={{ letterSpacing: "-0.04em", lineHeight: 1.02 }}
      >
        {title}
      </h2>
      {body && <p className="max-w-2xl text-lg text-pretty text-muted-foreground">{body}</p>}
    </Reveal>
  );
}

type LandingPageProps = { isSignedIn: boolean };

export function LandingPage({ isSignedIn }: LandingPageProps) {
  const appHref = isSignedIn ? "/runs" : "/sign-in";
  const startLabel = isSignedIn ? "Open the app" : "Get started free";
  return (
    <SmoothScroll>
      <div className="relative flex min-h-screen flex-col overflow-x-clip">
        <header className="sticky top-0 z-30 border-b border-white/5 bg-background/60 backdrop-blur-xl">
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
              className="hidden items-center gap-7 text-sm text-muted-foreground md:flex"
            >
              <a href="#film" className="transition-colors hover:text-foreground">
                Film
              </a>
              <a href="#gap" className="transition-colors hover:text-foreground">
                Why not tracing
              </a>
              <a href="#how" className="transition-colors hover:text-foreground">
                How it works
              </a>
              <a href="#sdk" className="transition-colors hover:text-foreground">
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
          <Hero appHref={appHref} startLabel={startLabel} />

          <section id="film" aria-labelledby="film-title" className="scroll-mt-20">
            <div className="mx-auto flex w-full max-w-6xl flex-col gap-12 px-4 py-28 sm:px-6">
              <SectionHeading
                id="film-title"
                eyebrow="The film · 1:43"
                title="Every step recorded. None of it explained."
                body="Why tracing alone cannot tell you which step broke your agent, and how replaying from save points can."
              />
              <Film />
            </div>
          </section>

          <section id="gap" aria-labelledby="gap-title" className="scroll-mt-20">
            <div className="mx-auto flex w-full max-w-6xl flex-col gap-12 px-4 py-28 sm:px-6">
              <SectionHeading
                id="gap-title"
                eyebrow="Why not tracing"
                title="A trace shows what happened. Not why."
                body="Observability platforms are great at recording. When a run fails, an engineer still reads every step, guesses, and often fixes the wrong one."
              />
              <div className="grid gap-5 md:grid-cols-2">
                <Reveal>
                  <div className="flex h-full flex-col gap-6 rounded-2xl border bg-card/60 p-8">
                    <span className="font-mono text-sm text-muted-foreground">
                      Braintrust, LangSmith and other tracing
                    </span>
                    <ul className="flex flex-col gap-4">
                      {TRACING.map((item) => (
                        <li
                          key={item.text}
                          className={item.ok ? "flex gap-3" : "flex gap-3 text-muted-foreground"}
                        >
                          {item.ok ? (
                            <CheckIcon
                              className="mt-0.5 size-5 shrink-0 text-muted-foreground"
                              aria-hidden="true"
                            />
                          ) : (
                            <XIcon
                              className="mt-0.5 size-5 shrink-0 text-destructive"
                              aria-hidden="true"
                            />
                          )}
                          {item.text}
                        </li>
                      ))}
                    </ul>
                  </div>
                </Reveal>
                <Reveal delay={0.12}>
                  <div
                    className="relative flex h-full flex-col gap-6 overflow-hidden rounded-2xl border border-domino/40 bg-card p-8"
                    style={{
                      boxShadow:
                        "0 0 80px -20px color-mix(in srgb, var(--domino) 45%, transparent)",
                    }}
                  >
                    <span className="font-mono text-sm text-domino">First Domino</span>
                    <ul className="flex flex-col gap-4">
                      {FIRST_DOMINO.map((text) => (
                        <li key={text} className="flex gap-3 font-medium">
                          <CheckIcon
                            className="mt-0.5 size-5 shrink-0 text-domino"
                            aria-hidden="true"
                          />
                          {text}
                        </li>
                      ))}
                    </ul>
                  </div>
                </Reveal>
              </div>
            </div>
          </section>

          <section
            id="how"
            aria-label="How it works"
            className="scroll-mt-20 border-t border-white/5"
          >
            <BisectStory />
          </section>

          <section
            id="why"
            aria-labelledby="why-title"
            className="scroll-mt-20 border-t border-white/5"
          >
            <div className="mx-auto flex w-full max-w-6xl flex-col gap-12 px-4 py-28 sm:px-6">
              <SectionHeading
                id="why-title"
                eyebrow="Why First Domino"
                title="Other tools tell you a run failed. This one tells you why, with proof."
              />
              <div className="grid gap-5 md:grid-cols-3">
                {PRINCIPLES.map((item, i) => (
                  <Reveal key={item.title} delay={i * 0.1}>
                    <SpotlightCard className="h-full">
                      <item.icon className="size-6 text-domino" aria-hidden="true" />
                      <h3 className="mt-5 text-lg font-semibold">{item.title}</h3>
                      <p className="mt-2 text-pretty text-muted-foreground">{item.body}</p>
                    </SpotlightCard>
                  </Reveal>
                ))}
              </div>
            </div>
          </section>

          <section
            id="sdk"
            aria-labelledby="sdk-title"
            className="scroll-mt-20 border-t border-white/5"
          >
            <div className="mx-auto grid w-full max-w-6xl items-center gap-14 px-4 py-28 sm:px-6 lg:grid-cols-2">
              <div className="flex flex-col gap-6">
                <SectionHeading
                  id="sdk-title"
                  eyebrow="Python SDK · MIT"
                  title="Add two lines. Run one worker. Done."
                  body="Mark the function that runs your agent, and every model call inside it is recorded live. A failed run is diagnosed on its own, and the worker replays it next to your agent."
                />
                <Reveal
                  delay={0.1}
                  className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground"
                >
                  <code className="rounded-md border bg-card px-3 py-1.5 font-mono text-foreground">
                    pip install first-domino
                  </code>
                  or
                  <code className="rounded-md border bg-card px-3 py-1.5 font-mono text-foreground">
                    uv add first-domino
                  </code>
                </Reveal>
              </div>
              <Reveal delay={0.15}>
                <div className="overflow-hidden rounded-xl border border-white/10 shadow-2xl shadow-black/50">
                  <div
                    className="flex h-9 items-center justify-between border-b border-black/40 px-4"
                    style={{ background: "linear-gradient(#2c2c31, #242428)" }}
                  >
                    <span className="font-mono text-xs text-white/50">agent.py</span>
                    <span className="font-mono text-xs text-white/40">python</span>
                  </div>
                  <pre
                    className="overflow-x-auto py-4 font-mono text-sm leading-7"
                    style={{ background: "rgba(15,15,18,0.97)" }}
                  >
                    {SDK_LINES.map((line, i) => (
                      <div
                        key={i}
                        className="px-5"
                        style={
                          line.hot
                            ? {
                                background: "color-mix(in srgb, var(--domino) 12%, transparent)",
                                boxShadow: "inset 3px 0 0 var(--domino)",
                              }
                            : undefined
                        }
                      >
                        <span className="mr-5 inline-block w-4 text-right text-white/25 select-none">
                          {i + 1}
                        </span>
                        {line.spans.map((span, j) => (
                          <span key={j} style={{ color: span.tone ? TONE[span.tone] : "#e4e4e7" }}>
                            {span.text}
                          </span>
                        ))}
                      </div>
                    ))}
                  </pre>
                </div>
              </Reveal>
            </div>
          </section>

          <section className="border-t border-white/5">
            <div className="mx-auto w-full max-w-6xl px-4 py-36 sm:px-6">
              <Closing appHref={appHref} startLabel={startLabel} />
            </div>
          </section>
        </main>

        <footer className="border-t border-white/5">
          <div className="mx-auto flex w-full max-w-6xl flex-col gap-2 px-4 py-8 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between sm:px-6">
            <BrandName />
            <span>Proven root causes for failed AI agent runs.</span>
          </div>
        </footer>
      </div>
    </SmoothScroll>
  );
}
