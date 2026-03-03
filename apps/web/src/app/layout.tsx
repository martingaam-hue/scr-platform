import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import { ThemeProvider } from "@/components/theme-provider";
import { QueryProvider } from "@/lib/query-provider";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });

// Prevent static prerendering — ClerkProvider requires the publishable key
// at render time, which isn't available during Docker build.
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "SCR Platform — Investment Intelligence",
  description:
    "Connecting impact project developers with professional investors through AI-powered intelligence.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider
        afterSignInUrl="/dashboard"
        afterSignUpUrl="/onboarding"
      >
      <html lang="en" suppressHydrationWarning>
        <body className={`${inter.variable} font-sans antialiased`}>
          <ThemeProvider
            attribute="class"
            defaultTheme="light"
            enableSystem
            disableTransitionOnChange
          >
            <QueryProvider>{children}</QueryProvider>
          </ThemeProvider>
        </body>
      </html>
    </ClerkProvider>
  );
}
