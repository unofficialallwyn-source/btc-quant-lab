import { cn } from "@/lib/utils";

export function AdPlaceholder({ label, className }: { label: string; className?: string }) {
  return (
    <div className={cn("rounded-xl border border-dashed border-border bg-muted/40 p-4 text-center text-xs text-slate-500", className)}>
      Ad Placeholder: {label}
    </div>
  );
}
