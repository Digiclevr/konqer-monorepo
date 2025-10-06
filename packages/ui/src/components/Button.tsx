import * as React from "react";

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary";
};

export function Button({ variant = "primary", className = "", ...rest }: ButtonProps) {
  const base =
    "inline-flex items-center justify-center rounded-2xl px-4 py-2 text-sm font-medium transition-all shadow-soft";
  const styles =
    variant === "primary"
      ? "bg-black text-white hover:opacity-90"
      : "bg-white text-black border border-neutral-200 hover:bg-neutral-50";
  return <button className={`${base} ${styles} ${className}`} />;
}
