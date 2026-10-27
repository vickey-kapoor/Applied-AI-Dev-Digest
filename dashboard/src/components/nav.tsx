"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  Layers,
  Clock,
  BarChart3,
  Settings,
  Sparkles,
  Eye,
  Menu,
  X,
  Send,
  Loader2,
  Check,
  AlertCircle,
} from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { buttonVariants } from "@/components/ui/button";

const navigation = [
  { name: "Topics", href: "/topics", icon: Layers },
  { name: "Preview", href: "/preview", icon: Eye },
  { name: "History", href: "/history", icon: Clock },
  { name: "Stats", href: "/stats", icon: BarChart3 },
  { name: "Settings", href: "/settings", icon: Settings },
];

type SendStatus = "idle" | "sending" | "sent" | "error";

function Wordmark() {
  return (
    <span className="flex items-center gap-2.5">
      <span className="surface-highlight flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-e1">
        <Sparkles className="h-4 w-4" aria-hidden="true" />
      </span>
      <span className="flex flex-col leading-none">
        <span className="font-display text-sm font-bold tracking-tight text-foreground">
          AI Dev Digest
        </span>
        <span className="mt-0.5 font-mono text-[0.625rem] uppercase tracking-[0.12em] text-subtle-foreground">
          Daily
        </span>
      </span>
    </span>
  );
}

export function Nav() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [paused, setPaused] = useState(false);
  const [pauseLoading, setPauseLoading] = useState(false);
  const [sendStatus, setSendStatus] = useState<SendStatus>("idle");
  const [sendError, setSendError] = useState("");

  const closeMobile = useCallback(() => setMobileOpen(false), []);

  // Close mobile nav on route change — intentional cascading render for nav UX
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { setMobileOpen(false); }, [pathname]);

  useEffect(() => {
    fetch("/api/pause")
      .then((r) => r.json())
      .then((d) => setPaused(!!d.paused))
      .catch(() => {});
  }, []);

  const togglePause = useCallback(async () => {
    setPauseLoading(true);
    try {
      const res = await fetch("/api/pause", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ paused: !paused }),
      });
      if (res.ok) setPaused(!paused);
    } catch { /* ignore */ }
    setPauseLoading(false);
  }, [paused]);

  const sendTest = useCallback(async () => {
    setSendStatus("sending");
    setSendError("");
    try {
      const res = await fetch("/api/test-send", { method: "POST" });
      const data = await res.json();
      if (!res.ok) {
        setSendStatus("error");
        setSendError(data.error || "Send failed");
        setTimeout(() => setSendStatus("idle"), 4000);
        return;
      }
      setSendStatus("sent");
      setTimeout(() => setSendStatus("idle"), 3000);
    } catch {
      setSendStatus("error");
      setSendError("Network error");
      setTimeout(() => setSendStatus("idle"), 4000);
    }
  }, []);

  return (
    <>
      <header className="fixed inset-x-0 top-0 z-40 border-b border-border/80 bg-background/80 backdrop-blur-xl">
        <div className="mx-auto flex h-16 w-full max-w-[1180px] items-center gap-3 px-5 sm:px-8">
          {/* Mobile menu */}
          <button
            className="-ml-1.5 rounded-lg p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground md:hidden"
            onClick={() => setMobileOpen(true)}
            aria-label="Open menu"
          >
            <Menu className="h-5 w-5" />
          </button>

          {/* Brand */}
          <Link href="/topics" className="shrink-0 rounded-lg">
            <Wordmark />
          </Link>

          {/* Desktop nav — a segmented group rather than five loose links */}
          <nav
            className="ml-5 hidden items-center gap-0.5 rounded-xl border border-border bg-surface p-1 md:flex"
            aria-label="Main navigation"
          >
            {navigation.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  aria-current={isActive ? "page" : undefined}
                  className={cn(
                    "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
                    isActive
                      ? "surface-highlight bg-card text-foreground shadow-e1"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  <item.icon
                    className={cn(
                      "h-4 w-4",
                      isActive ? "text-primary" : "text-subtle-foreground",
                    )}
                  />
                  {item.name}
                </Link>
              );
            })}
          </nav>

          {/* Right side */}
          <div className="ml-auto flex items-center gap-2">
            {/* Send test button */}
            <button
              onClick={sendTest}
              disabled={sendStatus === "sending"}
              className={cn(
                buttonVariants({ variant: "secondary", size: "sm" }),
                "hidden sm:inline-flex",
                sendStatus === "sent" && "border-success/30 text-success",
                sendStatus === "error" &&
                  "border-destructive/30 text-destructive",
              )}
            >
              {sendStatus === "sending" ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : sendStatus === "sent" ? (
                <Check className="h-3.5 w-3.5" />
              ) : sendStatus === "error" ? (
                <AlertCircle className="h-3.5 w-3.5" />
              ) : (
                <Send className="h-3.5 w-3.5" />
              )}
              {sendStatus === "sending"
                ? "Sending..."
                : sendStatus === "sent"
                ? "Sent"
                : sendStatus === "error"
                ? sendError
                : "Send test"}
            </button>

            {/* Pause toggle */}
            <button
              onClick={togglePause}
              disabled={pauseLoading}
              aria-label={
                paused ? "Resume the daily digest" : "Pause the daily digest"
              }
              className={cn(
                "inline-flex h-8 items-center gap-2 rounded-lg border px-2.5 font-mono text-[0.6875rem] font-medium uppercase tracking-[0.08em] transition-colors disabled:opacity-60",
                paused
                  ? "border-warning/30 bg-warning/10 text-warning hover:bg-warning/15"
                  : "border-success/30 bg-success/10 text-success hover:bg-success/15",
              )}
            >
              <span className="relative flex h-1.5 w-1.5">
                {!paused && (
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-60" />
                )}
                <span
                  className={cn(
                    "relative inline-flex h-1.5 w-1.5 rounded-full",
                    paused ? "bg-warning" : "bg-success",
                  )}
                />
              </span>
              {paused ? "Paused" : "Active"}
            </button>
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Mobile overlay */}
      {mobileOpen && (
        <>
          <div
            className="fixed inset-0 z-50 bg-background/70 backdrop-blur-sm md:hidden"
            onClick={closeMobile}
            aria-hidden="true"
          />
          <div className="fixed inset-y-0 left-0 z-50 w-72 border-r border-border bg-card p-4 shadow-e3 md:hidden">
            <div className="mb-7 flex items-center justify-between">
              <Wordmark />
              <button
                onClick={closeMobile}
                aria-label="Close menu"
                className="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <nav className="space-y-1">
              {navigation.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    aria-current={isActive ? "page" : undefined}
                    className={cn(
                      "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                      isActive
                        ? "bg-primary/10 text-primary"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground",
                    )}
                  >
                    <item.icon className="h-[18px] w-[18px]" />
                    {item.name}
                  </Link>
                );
              })}
            </nav>
            {/* Mobile send test */}
            <div className="mt-4 border-t border-border pt-4">
              <button
                onClick={() => { sendTest(); closeMobile(); }}
                disabled={sendStatus === "sending"}
                className={cn(
                  buttonVariants({ variant: "ghost", size: "md" }),
                  "w-full justify-start px-3",
                )}
              >
                <Send className="h-[18px] w-[18px]" />
                Send test message
              </button>
            </div>
          </div>
        </>
      )}
    </>
  );
}
