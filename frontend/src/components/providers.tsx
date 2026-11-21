"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import type { Session } from "next-auth";
import { SessionProvider } from "next-auth/react";
import { useState } from "react";

import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";

type ProvidersProps = { session: Session | null; children: React.ReactNode };

const SESSION_REFRESH_SECONDS = 5 * 60;

export function Providers({ session, children }: ProvidersProps) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 60 * 1000, refetchOnWindowFocus: false, retry: 1 },
        },
      })
  );

  return (
    <SessionProvider session={session} refetchInterval={SESSION_REFRESH_SECONDS}>
      <QueryClientProvider client={client}>
        <TooltipProvider>{children}</TooltipProvider>
        <Toaster richColors />
        {process.env.NODE_ENV === "development" && <ReactQueryDevtools initialIsOpen={false} />}
      </QueryClientProvider>
    </SessionProvider>
  );
}
