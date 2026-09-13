import { cn } from "@/lib/cn";
import type { ButtonHTMLAttributes } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "ghost" | "outline";
  size?: "sm" | "md";
};

export function Button({ className, variant = "primary", size = "md", ...props }: Props) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-sm font-medium transition-colors duration-(--motion-quick) disabled:opacity-50",
        size === "sm" ? "h-9 px-3 text-sm" : "h-11 px-4 text-sm",
        variant === "primary" && "bg-accent text-accent-fg hover:bg-accent-dim",
        variant === "ghost" && "bg-transparent text-muted hover:bg-bg-subtle hover:text-fg",
        variant === "outline" && "border border-border bg-transparent text-fg hover:bg-bg-subtle",
        className,
      )}
      {...props}
    />
  );
}
