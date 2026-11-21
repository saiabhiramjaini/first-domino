import { jwtVerify } from "jose";

// Must match fd_api.services.email_alerts: only the API, signing with the shared secret,
// can ask the web app to send an alert.
export const ALERT_TOKEN_ISSUER = "first-domino-api";
export const ALERT_TOKEN_AUDIENCE = "first-domino-web-alerts";

export async function isAlertToken(token: string, secret: string): Promise<boolean> {
  try {
    await jwtVerify(token, new TextEncoder().encode(secret), {
      algorithms: ["HS256"],
      issuer: ALERT_TOKEN_ISSUER,
      audience: ALERT_TOKEN_AUDIENCE,
    });
    return true;
  } catch {
    return false;
  }
}
