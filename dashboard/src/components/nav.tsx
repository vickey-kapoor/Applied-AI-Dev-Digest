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
import { buttonVariants } from "@/components/ui/button";

const navigation = [
  { name: "Topics", href: "/topics", icon: Layers, hint: "What to track" },
  { name: "Preview", href: "/preview", icon: Eye, hint: "Last message" },
  { name: "History", href: "/history", icon: Clock, hint: "Sent this week" },
  { name: "Stats", href: "/stats", icon: BarChart3, hint: "Topic wins" },
  { name: "Settings", href: "/settings", icon: Settings, hint: "Pipeline" },
];

type SendStatus = "idle" | "sending" | "sent" | "error";

function Wordmark() {
  return (
    <span className="flex items-center gap-2.5">
      <span className="surface-highlight flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-e1">
        <Sparkles className="h-4 w-4" aria-hidden="true" />
      </span>
      <span className="flex flex-col leading-none">
        <span className="font-display text-[0.9375rem] font-bold tracking-tight text-foreground">
          AI Dev Digest
        </span>
        <span className="mt-1 font-mono text-[0.625rem] uppercase tracking-[0.12em] text-subtle-foreground">
          Daily
        </span>
      </span>
    </span>
  );
}

/**
 * The app shell: a fixed left rail on desktop, a drawer on mobile. Every
 * control that acts on the pipeline as a whole — the run status, the test
 * send — lives at the foot of the rail rather than competing with the page
 * title, so the content column is only ever content.
 */
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

  const railBody = (
    <>
      <nav className="space-y-1" aria-label="Main navigation">
        {navigation.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 transition-colors",
                isActive
                  ? "surface-highlight bg-card text-foreground shadow-e1"
                  : "text-muted-foreground hover:bg-card/60 hover:text-foreground",
              )}
            >
              <item.icon
                className={cn(
                  "h-[18px] w-[18px] shrink-0",
                  isActive ? "text-primary" : "text-subtle-foreground",
                )}
              />
              <span className="flex min-w-0 flex-col leading-tight">
                <span className="text-sm font-medium">{item.name}</span>
                <span className="truncate text-[0.6875rem] text-subtle-foreground">
                  {item.hint}
                </span>
              </span>
            </Link>
          );
        })}
      </nav>

      {/* Pipeline controls sit at the foot of the rail */}
      <div className="mt-auto space-y-2 border-t border-border pt-4">
        <button
          onClick={togglePause}
          disabled={pauseLoading}
          aria-label={
            paused ? "Resume the daily digest" : "Pause the daily digest"
          }
          className={cn(
            "flex w-full items-center gap-2.5 rounded-lg border px-3 py-2 text-left transition-colors disabled:opacity-60",
            paused
              ? "border-warning/30 bg-warning/10 hover:bg-warning/15"
              : "border-success/30 bg-success/10 hover:bg-success/15",
          )}
        >
          <span className="relative flex h-2 w-2 shrink-0">
            {!paused && (
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-60" />
            )}
            <span
              className={cn(
                "relative inline-flex h-2 w-2 rounded-full",
                paused ? "bg-warning" : "bg-success",
              )}
            />
          </span>
          <span className="flex flex-col leading-tight">
            <span
              className={cn(
                "font-mono text-[0.6875rem] font-medium uppercase tracking-[0.08em]",
                paused ? "text-warning" : "text-success",
              )}
            >
              {paused ? "Paused" : "Active"}
            </span>
            <span className="text-[0.6875rem] text-muted-foreground">
              {paused ? "Click to resume" : "Click to pause"}
            </span>
          </span>
        </button>

        <button
          onClick={() => { sendTest(); closeMobile(); }}
          disabled={sendStatus === "sending"}
          className={cn(
            buttonVariants({ variant: "secondary", size: "md" }),
            "w-full justify-start",
            sendStatus === "sent" && "border-success/30 text-success",
            sendStatus === "error" && "border-destructive/30 text-destructive",
          )}
        >
          {sendStatus === "sending" ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : sendStatus === "sent" ? (
            <Check className="h-4 w-4" />
          ) : sendStatus === "error" ? (
            <AlertCircle className="h-4 w-4" />
          ) : (
            <Send className="h-4 w-4" />
          )}
          <span className="truncate">
            {sendStatus === "sending"
              ? "Sending..."
              : sendStatus === "sent"
              ? "Sent"
              : sendStatus === "error"
              ? sendError
              : "Send test"}
          </span>
        </button>
      </div>
    </>
  );

  return (
    <>
      {/* Desktop rail */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-60 flex-col border-r border-border bg-surface px-3 py-5 lg:flex">
        <Link href="/topics" className="mb-7 rounded-lg px-2">
          <Wordmark />
        </Link>
        {railBody}
      </aside>

      {/* Mobile top bar */}
      <header className="fixed inset-x-0 top-0 z-40 flex h-16 items-center gap-3 border-b border-border bg-background/85 px-4 backdrop-blur-xl lg:hidden">
        <button
          className="-ml-1 rounded-lg p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          onClick={() => setMobileOpen(true)}
          aria-label="Open menu"
        >
          <Menu className="h-5 w-5" />
        </button>
        <Link href="/topics" className="rounded-lg">
          <Wordmark />
        </Link>
        <span
          className={cn(
            "ml-auto flex h-2 w-2 rounded-full",
            paused ? "bg-warning" : "bg-success",
          )}
          aria-label={paused ? "Digest paused" : "Digest active"}
        />
      </header>

      {/* Mobile drawer */}
      {mobileOpen && (
        <>
          <div
            className="fixed inset-0 z-50 bg-background/70 backdrop-blur-sm lg:hidden"
            onClick={closeMobile}
            aria-hidden="true"
          />
          <div className="fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-border bg-surface px-3 py-5 shadow-e3 lg:hidden">
            <div className="mb-7 flex items-center justify-between px-2">
              <Wordmark />
              <button
                onClick={closeMobile}
                aria-label="Close menu"
                className="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            {railBody}
          </div>
        </>
      )}
    </>
  );
}
