import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AssetTrace",
  description: "Fixed Asset Verification & QR Code Management",
};

// This app is inherently per-request (every page depends on who's signed
// in), but nothing in it calls a Next.js API that signals that on its own —
// Prisma queries don't count. Without this, `next build` can statically
// prerender pages like "/" using whatever session state existed at build
// time and serve that frozen snapshot forever in production.
export const dynamic = "force-dynamic";

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
