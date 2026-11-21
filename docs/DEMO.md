# Demo script

Three minutes, click by click, on the real "Equal AI (demo)" project. The presenter is signed in with Google at http://localhost:3000 before starting. Times are cumulative.

## URLs

| What | URL |
| --- | --- |
| Landing page | http://localhost:3000 |
| Failures inbox | http://localhost:3000/failures |
| Run b02, AM saved as PM | http://localhost:3000/runs/77849acb-bc71-4097-8a94-29d4fbf19e70 |
| Root cause "Converted AM appointment to PM" | http://localhost:3000/causes/88a0808b-955f-46d2-abfe-35cce9960873 |
| Root causes | http://localhost:3000/causes |
| Benchmark | http://localhost:3000/benchmark |
| API health | http://localhost:8000/health |

A second b02 run (`11c757f8`) also exists; either tells the same story. Ids change if the project is seeded again: then open b02 from the inbox (agent `call-assistant`, 10 steps, the clinic call for Mr. Arjun Rao).

## Script

**0:00 The problem (one line).**
"When an AI agent fails, the trace shows what happened, not which step doomed the run. First Domino finds that step and proves it."

**0:10 Failures inbox.** Open `/failures`.
- Point at the counts: failed runs, root causes, diagnoses done, verified by a fix.
- "This is Equal AI's call assistant: it answers calls, adds calendar events, reminders and callbacks. Every failed call has already been diagnosed automatically."
- Point at "Top root causes" on the right: the same mistakes group together.
- Click the b02 run (Mr. Arjun Rao's clinic call).

**0:35 The run.** On the run screen, top section.
- Read the task: the clinic calls to confirm a follow-up "tomorrow at 10". The final output says 10:00 AM, so the summary looks fine, yet the success check failed it.
- "Which of the 10 steps doomed this call? Reading the trace, you would guess."

**0:55 The checks.** Scroll to "Checks" (bottom right), then back up to the step strip.
- "We replay the agent from its own save points. A fresh run succeeds 3 of 3, so the task is fine. Keep steps 1 to 5: still succeeds. Keep 1 to 8, 1 to 7, 1 to 6: every replay fails."
- "So step 6 is the first domino: from step 5 the call can still succeed, from step 6 it never does." Point at the orange step 6 in the strip; everything else is ruled out.
- Checks 6, replays 20, cost about one and a half cents.

**1:25 The proof.** Verdict card under the strip.
- Badges: **Verified**, **Wrong date**. Title: "Converted AM appointment to PM".
- Original step 6 (left): the agent adds a second calendar event at 22:00. Fixed step 6 (right): it replies to the caller confirming 10 AM.
- Read the proof line: **"5 of 5 replays passed with the fixed step."** "We changed one step and the call passes. That is a proof, not a guess."
- Point at the suggested fix.

**1:50 Root causes.** Click "See runs with this cause", then "All root causes".
- "Converted AM appointment to PM" has 3 runs, 3 verified. Five cause groups in all: wrong contact, spam treated as genuine, "tomorrow" resolved a day late, a hallucinated reminder.
- "Your team fixes five causes, not eight tickets."

**2:10 Benchmark.** Open `/benchmark`.
- "On labelled failed runs, First Domino names the exact step **82%** of the time; an LLM judge reading the trace gets **74%**. Most of our answers also come with a replay proof (the "Proven by replay" column); the judge can never prove its answer."
- Mention the cost and time columns honestly: replays cost more and take longer than one judge call.

**2:30 Live.** In a terminal in `server/`:

```bash
make demo-live BUG=b02
```

- Open the URL it prints. The run screen shows the diagnosis live: the blue search range narrows step by step, the checks list fills in, step 6 turns orange when verify starts, and the verdict card appears when the fix passes.
- "Everything you just saw ran on our worker against the customer's own agent; the agent and its secrets never leave their side."

**3:00 End.**

## If something breaks

Restart in this order, each in its own terminal. Check each step before starting the next.

1. **Postgres:** `cd server && make db-up`. Waits until healthy.
2. **API on :8000:** `cd server && make api`. Needs `server/.env` with the OpenAI key, the engine models and `FD_API_WEB_JWT_SECRET` (same value as `API_JWT_SECRET` in `client/.env.local`). Check http://localhost:8000/health answers `{"ok": true}`.
3. **Worker:** `cd server && make worker`. Needs `FIRST_DOMINO_API_KEY` for the "Equal AI (demo)" project in `server/.env` (`make seed-demo EMAIL=<presenter's Google email>` prints one).
4. **Web on :3000:** `cd client && bun run dev`. Check http://localhost:3000/api/health.

| Symptom | Cause and fix |
| --- | --- |
| Red "Could not reach the API" boxes | The API on :8000 is down. Restart step 2, then click "Try again". |
| Red "Your session has expired" boxes | The API rejects the web token: `FD_API_WEB_JWT_SECRET` is missing or differs from `API_JWT_SECRET`. Fix `server/.env` and restart the API. |
| Sign-in page instead of the inbox | Sign in with Google again. |
| Inbox shows a different project or all zeros | Signed in with another Google account, or the project was not seeded for this email. Run `make seed-demo EMAIL=...`. |
| A live diagnosis stays "Queued" | No worker is running. Start step 3. |
| A diagnosis ends "No replay came back" | The worker cannot reach the API or has the wrong key. Check step 3, then click "Diagnose again". |
