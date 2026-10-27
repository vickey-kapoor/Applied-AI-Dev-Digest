import * as React from "react";
import type { LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  children?: React.ReactNode;
}

/** Shared "nothing here yet" panel, so every empty page reads the same. */
export function EmptyState({
  icon: Icon,
  title,
  description,
  children,
}: EmptyStateProps) {
  return (
    <Card elevation="flat" className="bg-surface">
      <CardContent className="flex flex-col items-center justify-center px-6 py-20 text-center">
        <span className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl border border-border bg-card text-subtle-foreground shadow-e1">
          <Icon className="h-6 w-6" aria-hidden="true" />
        </span>
        <p className="font-display text-lg font-semibold text-foreground">
          {title}
        </p>
        <p className="mt-2 max-w-sm text-sm leading-relaxed text-muted-foreground">
          {description}
        </p>
        {children && <div className="mt-6">{children}</div>}
      </CardContent>
    </Card>
  );
}
