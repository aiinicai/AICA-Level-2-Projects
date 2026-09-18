import type { Metadata } from "next"
import { Inter, Public_Sans, Plus_Jakarta_Sans } from "next/font/google"
import "./globals.css"
import { Providers } from "@/components/layout/providers"
import { Toaster } from "@/components/ui/toast"

const inter = Inter({ subsets: ["latin"], variable: "--font-body" })
const publicSans = Public_Sans({ subsets: ["latin"], variable: "--font-sans" })
const plusJakartaSans = Plus_Jakarta_Sans({ subsets: ["latin"], variable: "--font-display" })

export const metadata: Metadata = {
  title: "TaxFlow - Indirect Tax Compliance Platform",
  description: "Enterprise indirect tax compliance management system",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} ${publicSans.variable} ${plusJakartaSans.variable}`}>
        <Providers>
          {children}
          <Toaster />
        </Providers>
      </body>
    </html>
  )
}
