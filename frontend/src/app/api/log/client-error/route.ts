import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

import { getIp } from "@/lib/get-ip";
import { log } from "@/lib/log";

export const runtime = "nodejs";

const ClientErrorSchema = z.object({
  message: z.string().min(1).max(2_000),
  stack: z.string().max(8_000).optional(),
  source: z.string().min(1).max(50),
  url: z.string().max(2_000).optional(),
});

const REPORTS_PER_MINUTE = 10;
const buckets = new Map<string, { count: number; resetAt: number }>();

function allow(ip: string): boolean {
  const now = Date.now();
  const bucket = buckets.get(ip);
  if (!bucket || bucket.resetAt <= now) {
    buckets.set(ip, { count: 1, resetAt: now + 60_000 });
    return true;
  }
  if (bucket.count >= REPORTS_PER_MINUTE) return false;
  bucket.count += 1;
  return true;
}

export async function POST(req: NextRequest): Promise<NextResponse> {
  const origin = req.headers.get("origin");
  const app = process.env.NEXT_PUBLIC_APP_URL;
  if (origin && app && origin !== new URL(app).origin) {
    return new NextResponse(null, { status: 204 });
  }
  if (Number(req.headers.get("content-length") ?? 0) > 12_000) {
    return new NextResponse(null, { status: 413 });
  }
  const ip = getIp(req);
  if (!allow(ip)) return new NextResponse(null, { status: 429 });
  const parsed = ClientErrorSchema.safeParse(await req.json().catch(() => null));
  if (!parsed.success) return new NextResponse(null, { status: 400 });
  const err = new Error(parsed.data.message);
  if (parsed.data.stack) err.stack = parsed.data.stack;
  log.error(
    { err, source: parsed.data.source, client: { url: parsed.data.url, ip } },
    "client.error_reported"
  );
  return new NextResponse(null, { status: 204 });
}
