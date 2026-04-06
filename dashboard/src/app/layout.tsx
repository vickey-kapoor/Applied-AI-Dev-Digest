import type { Metadata } from "next";
import { DM_Mono, Syne } from "next/font/google";
import "./globals.css";
import { Nav } from "@/components/nav";
import { cn } from "@/lib/utils";

const dmMono = DM_Mono({ weight: "400", subsets: ["latin"], variable: "--font-dm-mono" });
const syne = Syne({ subsets: ["latin"], variable: "--font-syne" });

export const metadata: Metadata = {
  title: "AI Dev Digest",
  description: "Dashboard for tracking developer product updates from AI labs",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={cn(dmMono.variable, syne.variable)}>
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:top-2 focus:left-2 focus:px-4 focus:py-2 focus:bg-primary focus:text-white focus:rounded-lg"
        >
          Skip to main content
        </a>
        <Nav />
        <main id="main-content" className="min-h-screen pt-14" style={{ maxWidth: '1100px', margin: '0 auto', paddingLeft: '24px', paddingRight: '24px' }}>
          {children}
        </main>
      </body>
    </html>
  );
}
