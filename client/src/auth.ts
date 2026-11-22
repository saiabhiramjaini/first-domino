import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import Google from "next-auth/providers/google";

import { apiTokenNeedsRefresh, mintApiToken } from "@/lib/api-token";
import { checkDemoLogin, demoSubject } from "@/lib/demo-login";
import { log } from "@/lib/log";
import { apiJwtSecret, demoLogin } from "@/lib/server-env";

export const SIGN_IN_PATH = "/sign-in";
export const DEMO_PROVIDER = "demo";

// The shared test account, only when DEMO_LOGIN_EMAIL and DEMO_LOGIN_PASSWORD are set.
const demo = demoLogin();
const demoProvider = demo
  ? [
      Credentials({
        id: DEMO_PROVIDER,
        name: "Test login",
        credentials: { email: {}, password: {} },
        authorize: (credentials) => checkDemoLogin(demo, credentials.email, credentials.password),
      }),
    ]
  : [];

export const { handlers, auth, signIn } = NextAuth({
  providers: [Google, ...demoProvider],
  session: { strategy: "jwt" },
  pages: { signIn: SIGN_IN_PATH },
  callbacks: {
    async jwt({ token, account, trigger }) {
      if (account?.provider === "google") token.googleId = account.providerAccountId;
      if (account?.provider === DEMO_PROVIDER && demo) token.googleId = demoSubject(demo.email);
      const nowSeconds = Math.floor(Date.now() / 1000);
      const isForced = trigger === "update";
      if (
        !token.googleId ||
        (!isForced && !apiTokenNeedsRefresh(token.apiTokenExpiresAt, nowSeconds))
      ) {
        return token;
      }
      try {
        const minted = await mintApiToken(
          { googleId: token.googleId, email: token.email ?? null, name: token.name ?? null },
          apiJwtSecret(),
          nowSeconds
        );
        token.apiToken = minted.token;
        token.apiTokenExpiresAt = minted.expiresAt;
      } catch (err) {
        log.error({ err }, "auth.api_token_mint_failed");
      }
      return token;
    },
    session({ session, token }) {
      session.apiToken = token.apiToken;
      return session;
    },
  },
});
