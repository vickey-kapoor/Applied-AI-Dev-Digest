"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  Home,
  FileText,
  FolderOpen,
  BarChart3,
  Settings,
  Brain,
  ListTodo,
  Menu,
  X,
} from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";

const navigation = [
  { name: "Dashboard", href: "/", icon: Home },
  { name: "Updates", href: "/papers", icon: FileText },
  { name: "Backlog", href: "/backlog", icon: ListTodo },
  { name: "Reports", href: "/reports", icon: FolderOpen },
  { name: "Analytics", href: "/analytics", icon: BarChart3 },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  const closeMobile = useCallback(() => setMobileOpen(false), []);

  // Close on route change — track previous pathname to avoid calling setState unconditionally
  const [prevPathname, setPrevPathname] = useState(pathname);
  if (pathname !== prevPathname) {
    setPrevPathname(pathname);
    if (mobileOpen) {
      setMobileOpen(false);
    }
  }

  // Close on Escape key
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") closeMobile();
    }
    if (mobileOpen) {
      document.addEventListener("keydown", handleKey);
      return () => document.removeEventListener("keydown", handleKey);
    }
  }, [mobileOpen, closeMobile]);

  const sidebarContent = (
    <>
      {/* Logo */}
      <div className="flex h-16 items-center gap-2 px-6 border-b border-gray-200 dark:border-gray-700">
        <Brain className="h-8 w-8 text-blue-600" />
        <div className="flex flex-col">
          <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">AI Dev Digest</span>
          <span className="text-xs text-gray-500 dark:text-gray-400">Product Tracker</span>
        </div>
        {/* Close button on mobile */}
        <button
          className="ml-auto md:hidden p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
          onClick={closeMobile}
          aria-label="Close navigation menu"
        >
          <X className="h-5 w-5 text-gray-500" />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4" aria-label="Main navigation">
        <ul className="space-y-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href;
            return (
              <li key={item.name}>
                <Link
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                      : "text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                  )}
                >
                  <item.icon className={cn("h-5 w-5", isActive ? "text-blue-600 dark:text-blue-400" : "text-gray-400")} />
                  {item.name}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Footer */}
      <div className="border-t border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs text-gray-500 dark:text-gray-400">Theme</span>
          <ThemeToggle />
        </div>
        <div className="rounded-lg bg-gray-50 dark:bg-gray-800 p-3">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Daily updates at 10:00 AM CST
          </p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
            via GitHub Actions
          </p>
        </div>
      </div>
    </>
  );

  return (
    <>
      {/* Mobile hamburger button */}
      <button
        className="fixed top-3 left-3 z-50 md:hidden p-2 rounded-lg bg-white dark:bg-gray-800 shadow-md border border-gray-200 dark:border-gray-700"
        onClick={() => setMobileOpen(true)}
        aria-label="Open navigation menu"
      >
        <Menu className="h-5 w-5 text-gray-700 dark:text-gray-300" />
      </button>

      {/* Desktop sidebar */}
      <div className="hidden md:flex h-full w-64 flex-col bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700">
        {sidebarContent}
      </div>

      {/* Mobile overlay */}
      {mobileOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/50 md:hidden"
            onClick={closeMobile}
            aria-hidden="true"
          />
          <div className="fixed inset-y-0 left-0 z-50 w-64 flex flex-col bg-white dark:bg-gray-900 shadow-xl md:hidden">
            {sidebarContent}
          </div>
        </>
      )}
    </>
  );
}
