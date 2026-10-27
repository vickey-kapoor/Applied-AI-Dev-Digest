import * as React from "react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface PageHeaderProps {
  /** Small uppercase label above the title. */
  eyebrow: string;
  title: string;
  description: React.ReactNode;
  icon: LucideIcon;
  /** Short figure shown to the right of the title block, e.g. "8 / 11". */
  metric?: { value: React.ReactNode; label: string };
  /** Buttons rendered on the trailing edge. */
  actions?: React.ReactNode;
  className?: string;
}

/**
 * One header for every page: icon tile, eyebrow, display title, supporting
 * line, and an optional figure. Having the pages share it is what keeps the
 * vertical rhythm identical as you move between them.
 */
export function PageHeader({
  eyebrow,
  title,
  description,
  icon: Icon,
  metric,
  actions,
  className,
}: PageHeaderProps) {
  return (
    <header
      className={cn(
        "flex flex-col gap-5 border-b border-border pb-7 pt-10 sm:flex-row sm:items-end sm:justify-between",
        className,
      )}
    >
      <div className="flex items-start gap-4">
        <span className="surface-highlight mt-0.5 flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-primary/20 bg-primary/10 text-primary shadow-e1">
          <Icon className="h-5 w-5" aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <p className="eyebrow">{eyebrow}</p>
          <h1 className="mt-1.5 font-display text-3xl font-bold leading-none text-foreground sm:text-[2rem]">
            {title}
          </h1>
          <p className="mt-2.5 max-w-xl text-sm leading-relaxed text-muted-foreground">
            {description}
          </p>
        </div>
      </div>

      {(metric || actions) && (
        <div className="flex shrink-0 items-end gap-5 sm:pb-1">
          {metric && (
            <div className="sm:text-right">
              <p className="font-mono text-2xl font-semibold leading-none tracking-tight text-foreground">
                {metric.value}
              </p>
              <p className="eyebrow mt-2">{metric.label}</p>
            </div>
          )}
          {actions}
        </div>
      )}
    </header>
  );
}
