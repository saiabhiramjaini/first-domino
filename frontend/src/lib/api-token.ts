import { SignJWT } from "jose";

export const API_TOKEN_ISSUER = "first-domino-web";
export const API_TOKEN_AUDIENCE = "first-domino-api";
export const API_TOKEN_LIFETIME_SECONDS = 60 * 60;
export const API_TOKEN_REFRESH_MARGIN_SECONDS = 5 * 60;

export type ApiTokenSubject = {
  googleId: string;
  email: string | null;
  name: string | null;
};

export type MintedApiToken = { token: string; expiresAt: number };

export async function mintApiToken(
  subject: ApiTokenSubject,
  secret: string,
  nowSeconds: number
): Promise<MintedApiToken> {
  const expiresAt = nowSeconds + API_TOKEN_LIFETIME_SECONDS;
  const token = await new SignJWT({ email: subject.email, name: subject.name })
    .setProtectedHeader({ alg: "HS256", typ: "JWT" })
    .setSubject(subject.googleId)
    .setIssuer(API_TOKEN_ISSUER)
    .setAudience(API_TOKEN_AUDIENCE)
    .setIssuedAt(nowSeconds)
    .setExpirationTime(expiresAt)
    .sign(new TextEncoder().encode(secret));
  return { token, expiresAt };
}

export function apiTokenNeedsRefresh(expiresAt: number | undefined, nowSeconds: number): boolean {
  return expiresAt === undefined || expiresAt - nowSeconds < API_TOKEN_REFRESH_MARGIN_SECONDS;
}
