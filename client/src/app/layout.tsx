import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";

import { auth } from "@/auth";
import { Providers } from "@/components/providers";

import "./globals.css";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });
const jetbrainsMono = JetBrains_Mono({ variable: "--font-jetbrains-mono", subsets: ["latin"] });

const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";
const DESCRIPTION = "Find the step where your AI agent's run started to fall. Proven, not guessed.";

// The app is dark only.
export const viewport: Viewport = { themeColor: "#0a0a0b", colorScheme: "dark" };

export const metadata: Metadata = {
  metadataBase: new URL(APP_URL),
  title: { default: "First Domino", template: "%s | First Domino" },
  description: DESCRIPTION,
  openGraph: {
    title: "First Domino",
    description: DESCRIPTION,
    type: "website",
    url: APP_URL,
    siteName: "First Domino",
  },
  robots: { index: true, follow: true },
};

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const session = await auth();
  return (
    <html
      lang="en"
      className={`${inter.variable} ${jetbrainsMono.variable} dark h-full antialiased`}
      suppressHydrationWarning
    >
      <body className="flex min-h-full flex-col">
        <Providers session={session}>{children}</Providers>
      </body>
    </html>
  );
}
