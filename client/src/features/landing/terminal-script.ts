// What the hero terminal shows at any moment: a real zsh session that installs the SDK, shows the
// two added lines, runs the agent, and watches the worker find and prove the failing step.
// Pure, so any moment can be drawn (and tested) exactly.

export type Color =
  | "fg"
  | "dim"
  | "green"
  | "cyan"
  | "blue"
  | "red"
  | "yellow"
  | "magenta"
  | "violet"
  | "string"
  | "comment";
export type Span = { text: string; color?: Color; bold?: boolean };
export type Line = Span[];
export type Frame = {
  lines: Line[];
  /** Index of the line holding the cursor, or null while a command prints. */
  cursorLine: number | null;
};

type Entry = { start: number; render: (elapsed: number) => Line; prompt?: boolean };

const BAR = 30;
const SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];
const THINK_MS = 650; // the prompt waits a moment before typing starts

/** zsh with oh-my-zsh: the arrow turns red after a command that failed. */
const prompt = (ok: boolean): Span[] => [
  { text: "➜  ", color: ok ? "green" : "red", bold: true },
  { text: "agent ", color: "cyan", bold: true },
  { text: "git:(", color: "blue", bold: true },
  { text: "main", color: "red", bold: true },
  { text: ") ", color: "blue", bold: true },
];

/** Typing rhythm: steady, with small human variations that repeat on every loop. */
function typingTimes(text: string): number[] {
  const times: number[] = [];
  let t = THINK_MS;
  for (let i = 0; i < text.length; i++) {
    const wobble = ((i * 7919 + text.length * 104729) % 37) - 18; // -18..18 ms
    t += 46 + wobble + (text[i] === " " ? 30 : 0);
    times.push(t);
  }
  return times;
}

const code = (n: number, spans: Span[]): Line => [{ text: `   ${n}   │ `, color: "dim" }, ...spans];

function build() {
  const entries: Entry[] = [];
  let t = 0;
  let ok = true;

  // A prompt that appears, waits, then is typed into; enter is pressed `after` ms later.
  const command = (cmd: string, after: number) => {
    const times = typingTimes(cmd);
    const lastOk = ok;
    entries.push({
      start: t,
      prompt: true,
      render: (e) => [
        ...prompt(lastOk),
        { text: cmd.slice(0, times.filter((at) => at <= e).length) },
      ],
    });
    t += (times.at(-1) ?? 0) + after;
  };
  const line = (l: Line, gap = 60) => {
    entries.push({ start: t, render: () => l });
    t += gap;
  };

  // 1. Install, with pip's live download bar.
  command("pip install first-domino", 380);
  line([{ text: "Collecting first-domino" }], 260);
  line([{ text: "  Downloading first_domino-0.1.2-py3-none-any.whl.metadata (5.1 kB)" }], 120);
  line([{ text: "Downloading first_domino-0.1.2-py3-none-any.whl (48 kB)" }], 40);
  entries.push({
    start: t,
    render: (e) => {
      const p = Math.min(1, e / 900);
      const filled = Math.round(BAR * p);
      const done = p >= 1;
      return [
        { text: "   " },
        { text: "━".repeat(filled), color: done ? "green" : "magenta" },
        { text: "━".repeat(BAR - filled), color: "dim" },
        { text: ` ${(48.6 * p).toFixed(1)}/48.6 kB `, color: "green" },
        { text: done ? "2.1 MB/s" : `${(1.2 + p).toFixed(1)} MB/s`, color: "red" },
        { text: " eta " },
        { text: done ? "0:00:00" : "0:00:01", color: "cyan" },
      ];
    },
  });
  t += 1000;
  line([{ text: "Installing collected packages: first-domino" }], 520);
  line([{ text: "Successfully installed first-domino-0.1.2" }], 500);

  // 2. The two lines added to the agent, as bat shows a file.
  command("bat agent.py", 300);
  const rule = "───────";
  line([{ text: `${rule}┬${"─".repeat(46)}`, color: "dim" }], 30);
  line(
    [
      { text: "       │ File: ", color: "dim" },
      { text: "agent.py", bold: true },
    ],
    30
  );
  line([{ text: `${rule}┼${"─".repeat(46)}`, color: "dim" }], 30);
  line(
    code(1, [
      { text: "import ", color: "magenta" },
      { text: "first_domino " },
      { text: "as ", color: "magenta" },
      { text: "fd" },
    ]),
    30
  );
  line(code(2, []), 30);
  line(
    code(3, [
      { text: "@fd.entrypoint", color: "yellow" },
      { text: "(" },
      { text: '"refund-desk"', color: "string" },
      { text: ", check=refunded_right)" },
    ]),
    30
  );
  line(
    code(4, [
      { text: "def ", color: "magenta" },
      { text: "handle", color: "blue" },
      { text: "(request: " },
      { text: "str", color: "yellow" },
      { text: ") -> " },
      { text: "str", color: "yellow" },
      { text: ":" },
    ]),
    30
  );
  line(code(5, [{ text: "    ...  " }, { text: "# your agent, unchanged", color: "comment" }]), 30);
  line([{ text: `${rule}┴${"─".repeat(46)}`, color: "dim" }], 700);

  // 3. Run the agent: it fails the check, so the next prompt's arrow is red.
  command("python agent.py", 520);
  line([{ text: "agent: ", color: "dim" }, { text: "refunded $100 on order A-1001" }], 380);
  line(
    [
      { text: "first-domino: ", color: "dim" },
      { text: "run a1f3 failed your check", color: "red" },
      { text: " · 8 steps recorded", color: "dim" },
    ],
    700
  );
  ok = false;

  // 4. The worker replays and finds the first domino.
  command("python worker.py", 420);
  line([{ text: "first-domino worker · replaying run a1f3 on this machine", color: "dim" }], 260);
  const checks: [string, boolean][] = [
    ["keep steps 1–4", true],
    ["keep steps 1–6", false],
    ["keep steps 1–5", false],
  ];
  checks.forEach(([label, pass], i) => {
    entries.push({
      start: t,
      render: (e) => {
        const running = e < 1100;
        const mark: Span = running
          ? {
              text: SPINNER[Math.floor(e / 80) % SPINNER.length] ?? "⠋",
              color: "violet",
              bold: true,
            }
          : { text: pass ? "✓" : "✗", color: pass ? "green" : "red", bold: true };
        const head: Span[] = [mark, { text: ` check ${i + 1}  ${label}, replay the rest  ` }];
        if (running) return [...head, { text: "replaying 3 runs…", color: "dim" }];
        return [
          ...head,
          {
            text: pass ? "can pass (2/3)" : "always fails (0/6)",
            color: pass ? "green" : "red",
            bold: true,
          },
        ];
      },
    });
    t += 1300;
  });
  line(
    [
      { text: "◆ first domino: step 5", color: "violet", bold: true },
      { text: " · proven by replay, 3 of 3 pass with the fix" },
    ],
    160
  );
  line([{ text: "  → first-domino.abhiramtech.in/runs/a1f3", color: "blue" }], 400);

  // 5. Back at the prompt, idle, before the loop starts again.
  const lastOk = ok;
  entries.push({ start: t, prompt: true, render: () => prompt(lastOk) });
  t += 4200;
  return { entries, length: t };
}

const TIMELINE = build();
export const LOOP_MS = TIMELINE.length;
/** Lines a full terminal holds before it scrolls. */
export const ROWS = 19;

/** The terminal at `ms` milliseconds into the loop. */
export function terminalAt(ms: number): Frame {
  const t = ((ms % LOOP_MS) + LOOP_MS) % LOOP_MS;
  const shown = TIMELINE.entries.filter((e) => e.start <= t);
  let lines = shown.map((e) => e.render(t - e.start));
  let cursorLine = shown.at(-1)?.prompt ? lines.length - 1 : null;
  // Like a real terminal: once full, older lines scroll off the top.
  if (lines.length > ROWS) {
    const cut = lines.length - ROWS;
    lines = lines.slice(cut);
    if (cursorLine !== null) cursorLine -= cut;
  }
  return { lines, cursorLine };
}

/** Everything at the end, for people who prefer no motion. */
export function finalTerminal(): Frame {
  return terminalAt(LOOP_MS - 1);
}

/** A line as plain text: for tests and the accessible description. */
export const lineText = (line: Line) => line.map((s) => s.text).join("");
