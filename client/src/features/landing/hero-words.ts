/** The word above the rotating one. Change it here. */
export const HERO_LEAD = "Forget";

// Shared by the server-rendered heading (its accessible name) and the client animation, so it
// lives outside the "use client" component: a client module only exports components to the server.
// Every word is struck through: the tools that show every step but cannot say which one broke the
// run, then the habit they leave you with. The last word stays violet so the loop lands on it.
export const HERO_WORDS = [
  { text: "Braintrust.", accent: false },
  { text: "LangSmith.", accent: false },
  { text: "guessing.", accent: true },
] as const;
