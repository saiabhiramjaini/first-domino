import { NextResponse } from "next/server";

import { SIGN_IN_PATH, auth } from "@/auth";

export const proxy = auth((req) => {
  if (req.auth) return NextResponse.next();
  const signIn = new URL(SIGN_IN_PATH, req.nextUrl.origin);
  signIn.searchParams.set("callbackUrl", `${req.nextUrl.pathname}${req.nextUrl.search}`);
  return NextResponse.redirect(signIn);
});

export const config = {
  matcher: [
    "/failures/:path*",
    "/runs/:path*",
    "/causes/:path*",
    "/benchmark/:path*",
    "/settings/:path*",
  ],
};
