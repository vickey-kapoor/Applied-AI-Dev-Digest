import type { Metadata } from "next";
import { Inter, Syne } from "next/font/google";
import "./globals.css";
import { Nav } from "@/components/nav";
import { cn } from "@/lib/utils";

const inter = Inter({ subsets: ["latin"] });
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
    <html lang="en">
      <body className={cn(inter.className, syne.variable)}>
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:top-2 focus:left-2 focus:px-4 focus:py-2 focus:bg-primary focus:text-white focus:rounded-lg"
        >
          Skip to main content
        </a>
        <Nav />
        <main id="main-content" className="min-h-screen pt-14 max-w-[1100px] mx-auto px-6">
          {children}
        </main>
      </body>
    </html>
  );
}
