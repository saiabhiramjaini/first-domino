import "server-only";

function required(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is not set. Add it to client/.env.local.`);
  return value;
}

export function apiJwtSecret(): string {
  return required("API_JWT_SECRET");
}
