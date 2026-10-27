import { cva } from "class-variance-authority";

/**
 * Shared button recipe. The pages render plain <button>/<a> elements and pull
 * their classes from here, so every action on the dashboard has the same
 * height, radius, focus ring and hover behaviour.
 */
export const buttonVariants = cva(
  "inline-flex shrink-0 items-center justify-center gap-2 rounded-lg font-medium transition-[background-color,border-color,color,box-shadow,transform] duration-150 disabled:pointer-events-none disabled:opacity-50 active:translate-y-px",
  {
    variants: {
      variant: {
        primary:
          "bg-primary text-primary-foreground shadow-e1 hover:bg-primary/90 hover:shadow-e2",
        secondary:
          "border border-border bg-card text-foreground shadow-e1 hover:border-border-strong hover:bg-muted",
        ghost: "text-muted-foreground hover:bg-muted hover:text-foreground",
        solid:
          "bg-foreground text-background shadow-e1 hover:opacity-90 hover:shadow-e2",
        success: "bg-success text-white shadow-e1",
      },
      size: {
        sm: "h-8 px-3 text-xs",
        md: "h-9 px-4 text-sm",
        lg: "h-10 px-5 text-sm",
        icon: "h-8 w-8",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  },
);
