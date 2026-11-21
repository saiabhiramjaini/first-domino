import NextAuth from "next-auth";
import Google from "next-auth/providers/google";

import { apiTokenNeedsRefresh, mintApiToken } from "@/lib/api-token";
import { log } from "@/lib/log";
import { apiJwtSecret } from "@/lib/server-env";

export const SIGN_IN_PATH = "/sign-in";

export const { handlers, auth } = NextAuth({
  providers: [Google],
  session: { strategy: "jwt" },
  pages: { signIn: SIGN_IN_PATH },
  callbacks: {
    async jwt({ token, account, trigger }) {
      if (account?.provider === "google") token.googleId = account.providerAccountId;
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
