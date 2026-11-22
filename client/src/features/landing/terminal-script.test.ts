import { describe, expect, it } from "vitest";

import { finalTerminal, lineText, LOOP_MS, ROWS, terminalAt } from "./terminal-script";

const texts = (ms: number) => terminalAt(ms).lines.map(lineText);

describe("terminalAt", () => {
  it("opens on an empty prompt, then types the install command", () => {
    expect(texts(0)).toEqual(["➜  agent git:(main) "]);
    expect(terminalAt(0).cursorLine).toBe(0);
    expect(texts(2_200)[0]).toBe("➜  agent git:(main) pip install first-domino");
  });

  it("hides the cursor while a command prints", () => {
    const printing = Array.from({ length: 200 }, (_, i) => terminalAt(i * 50)).find(
      (f) => f.lines.length > 2 && f.cursorLine === null
    );
    expect(printing).toBeDefined();
  });

  it("fills pip's bar, then finishes the install", () => {
    const all = Array.from({ length: 300 }, (_, i) => texts(i * 25)).flat();
    expect(all.some((l) => l.includes("48.6/48.6 kB"))).toBe(true);
    expect(all.some((l) => l.includes("Successfully installed first-domino-0.1.2"))).toBe(true);
  });

  it("ends on the proven first domino, back at a red prompt, then loops", () => {
    const end = finalTerminal();
    const lines = end.lines.map(lineText);
    expect(lines).toContain("◆ first domino: step 5 · proven by replay, 3 of 3 pass with the fix");
    expect(lines.at(-1)).toBe("➜  agent git:(main) ");
    expect(end.lines.at(-1)?.[0]?.color).toBe("red");
    expect(end.cursorLine).toBe(end.lines.length - 1);
    expect(terminalAt(LOOP_MS)).toEqual(terminalAt(0));
  });

  it("never holds more lines than fit, like a real terminal scrolling", () => {
    for (let ms = 0; ms < LOOP_MS; ms += 113) {
      expect(terminalAt(ms).lines.length).toBeLessThanOrEqual(ROWS);
    }
  });
});
