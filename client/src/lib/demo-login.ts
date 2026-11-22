import type { DemoLogin } from "./server-env";

/** The API identity of the shared test account: not a Google id, so it never collides. */
export const demoSubject = (email: string) => `demo:${email}`;

/** Compares without stopping at the first difference, so timing does not leak the password. */
function sameText(a: string, b: string): boolean {
  const left = new TextEncoder().encode(a);
  const right = new TextEncoder().encode(b);
  let diff = left.length ^ right.length;
  for (let i = 0; i < Math.max(left.length, right.length); i++) {
    diff |= (left[i] ?? 0) ^ (right[i] ?? 0);
  }
  return diff === 0;
}

/** The user to sign in, or null when the email or password is wrong. */
export function checkDemoLogin(
  login: DemoLogin,
  email: unknown,
  password: unknown
): { id: string; email: string; name: string } | null {
  if (typeof email !== "string" || typeof password !== "string") return null;
  const emailOk = sameText(email.trim().toLowerCase(), login.email);
  const passwordOk = sameText(password, login.password);
  if (!emailOk || !passwordOk) return null;
  return { id: demoSubject(login.email), email: login.email, name: "Test reviewer" };
}
