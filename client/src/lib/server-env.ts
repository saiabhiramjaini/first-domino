import "server-only";

function required(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is not set. Add it to client/.env.local.`);
  return value;
}

export function apiJwtSecret(): string {
  return required("API_JWT_SECRET");
}

export type MailSender = { user: string; pass: string };

// The Gmail account alerts are sent from (with an app password), or null: alerts are off.
export function mailSender(): MailSender | null {
  const user = process.env.SENDER_EMAIL;
  const pass = process.env.SENDER_PASS;
  return user && pass ? { user, pass } : null;
}

export type DemoLogin = { email: string; password: string };

// A shared test account for reviewers who cannot use Google, or null: only Google sign-in.
export function demoLogin(): DemoLogin | null {
  const email = process.env.DEMO_LOGIN_EMAIL?.trim().toLowerCase();
  const password = process.env.DEMO_LOGIN_PASSWORD;
  return email && password ? { email, password } : null;
}
