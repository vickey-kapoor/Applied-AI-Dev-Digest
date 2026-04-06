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
  Brain,
  Eye,
  Menu,
  X,
  Send,
  Loader2,
  Check,
  AlertCircle,
} from "lucide-react";

const navigation = [
  { name: "Topics", href: "/topics", icon: Layers },
  { name: "Preview", href: "/preview", icon: Eye },
  { name: "History", href: "/history", icon: Clock },
  { name: "Stats", href: "/stats", icon: BarChart3 },
  { name: "Settings", href: "/settings", icon: Settings },
];

type SendStatus = "idle" | "sending" | "sent" | "error";

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
      <header className="fixed top-0 left-0 right-0 z-40 border-b border-border bg-background/95 backdrop-blur">
        <div className="flex items-center h-14 gap-4" style={{ maxWidth: '1100px', margin: '0 auto', padding: '0 24px' }}>
          {/* Mobile menu */}
          <button
            className="md:hidden p-1.5 rounded-lg hover:bg-card"
            onClick={() => setMobileOpen(true)}
            aria-label="Open menu"
          >
            <Menu className="h-5 w-5" />
          </button>

          {/* Brand */}
          <Link href="/topics" className="flex items-center gap-2 shrink-0">
            <Brain className="h-6 w-6 text-primary" />
            <span className="font-display font-bold text-sm text-foreground hidden sm:block">
              AI Dev Digest
            </span>
          </Link>

          {/* Desktop nav */}
          <nav className="hidden md:flex items-center gap-1 ml-4" aria-label="Main navigation">
            {navigation.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:text-foreground hover:bg-card"
                  )}
                >
                  <item.icon className="h-4 w-4" />
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
                "hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
                sendStatus === "sent"
                  ? "bg-green-900/30 text-green-400"
                  : sendStatus === "error"
                  ? "bg-red-900/30 text-red-400"
                  : "bg-card text-muted-foreground hover:bg-border hover:text-foreground"
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
              className={cn(
                "flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-mono font-medium transition-colors",
                paused
                  ? "bg-amber-900/30 text-amber-400"
                  : "bg-green-900/30 text-green-400"
              )}
            >
              <span className={cn("h-2 w-2 rounded-full", paused ? "bg-amber-500" : "bg-green-500")} />
              {paused ? "Paused" : "Active"}
            </button>
          </div>
        </div>
      </header>

      {/* Mobile overlay */}
      {mobileOpen && (
        <>
          <div className="fixed inset-0 z-50 bg-black/50 md:hidden" onClick={closeMobile} aria-hidden="true" />
          <div className="fixed inset-y-0 left-0 z-50 w-64 bg-card shadow-xl md:hidden p-4">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-2">
                <Brain className="h-6 w-6 text-primary" />
                <span className="font-display font-bold text-sm text-foreground">AI Dev Digest</span>
              </div>
              <button onClick={closeMobile} aria-label="Close menu" className="p-1 rounded-lg hover:bg-border">
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
                    className={cn(
                      "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                      isActive
                        ? "bg-primary/10 text-primary"
                        : "text-muted-foreground hover:bg-border hover:text-foreground"
                    )}
                  >
                    <item.icon className="h-5 w-5" />
                    {item.name}
                  </Link>
                );
              })}
            </nav>
            {/* Mobile send test */}
            <div className="mt-4 pt-4 border-t border-border">
              <button
                onClick={() => { sendTest(); closeMobile(); }}
                disabled={sendStatus === "sending"}
                className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium text-muted-foreground hover:bg-border hover:text-foreground transition-colors"
              >
                <Send className="h-5 w-5" />
                Send test message
              </button>
            </div>
          </div>
        </>
      )}
    </>
  );
}
