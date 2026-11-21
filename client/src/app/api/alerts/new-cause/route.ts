import { NextRequest, NextResponse } from "next/server";

import { isAlertToken } from "@/features/alerts/alert-token";
import { NewCauseAlertSchema, newCauseEmail } from "@/features/alerts/new-cause-email";
import { sendEmail } from "@/lib/email";
import { log } from "@/lib/log";
import { apiJwtSecret, mailSender } from "@/lib/server-env";

export const runtime = "nodejs";

// fd-api calls this when a new root cause is found; it emails the project's owner.
export async function POST(req: NextRequest): Promise<NextResponse> {
  const token = req.headers.get("authorization")?.replace(/^Bearer /, "");
  if (!token || !(await isAlertToken(token, apiJwtSecret()))) {
    return new NextResponse(null, { status: 401 });
  }
  const parsed = NewCauseAlertSchema.safeParse(await req.json().catch(() => null));
  if (!parsed.success) return new NextResponse(null, { status: 400 });
  const sender = mailSender();
  if (!sender) {
    log.warn("alerts.email_not_configured");
    return new NextResponse(null, { status: 503 });
  }
  const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? req.nextUrl.origin;
  const sent = await sendEmail(sender, newCauseEmail(parsed.data, appUrl));
  if (sent) log.info({ causeId: parsed.data.cause_id }, "alerts.new_cause_emailed");
  return new NextResponse(null, { status: sent ? 204 : 502 });
}
