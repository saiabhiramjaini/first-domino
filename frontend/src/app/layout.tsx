import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { Providers } from "@/components/providers";

import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";
const DESCRIPTION = "Find the step where your AI agent's run started to fall. Proven, not guessed.";

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

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
