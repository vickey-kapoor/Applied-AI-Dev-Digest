import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Syne } from "next/font/google";
import "./globals.css";
import { Nav } from "@/components/nav";
import { cn } from "@/lib/utils";

const inter = Inter({ subsets: ["latin"] });
const syne = Syne({ subsets: ["latin"], variable: "--font-syne" });
const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
});

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
      <body
        className={cn(inter.className, syne.variable, jetbrainsMono.variable)}
      >
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:top-3 focus:left-3 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-lg focus:shadow-e2"
        >
          Skip to main content
        </a>
        <Nav />
        <main
          id="main-content"
          className="min-h-screen pt-16 mx-auto w-full max-w-[1180px] px-5 sm:px-8"
        >
          {children}
        </main>
      </body>
    </html>
  );
}
