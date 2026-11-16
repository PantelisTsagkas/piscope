import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

/** A labelled form control with an optional hint and error message wired up for a11y. */
export function Field({
  id,
  label,
  hint,
  error,
  children,
  className,
}: {
  id: string;
  label: string;
  hint?: string;
  error?: string | null;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex min-w-0 flex-col gap-1.5", className)}>
      <Label htmlFor={id} className="font-mono text-[11px] tracking-wider uppercase">
        {label}
      </Label>
      {children}
      {error ? (
        <p id={`${id}-error`} role="alert" className="text-xs text-destructive">
          {error}
        </p>
      ) : hint ? (
        <p id={`${id}-hint`} className="text-xs text-muted-foreground">
          {hint}
        </p>
      ) : null}
    </div>
  );
}

/** A native select styled to match the inputs. Native keeps mobile and keyboard use simple. */
export function NativeSelect({ className, ...props }: React.ComponentProps<"select">) {
  return (
    <select
      className={cn(
        "h-8 w-full min-w-0 border border-input bg-input/30 px-2 font-mono text-xs text-foreground outline-none focus-visible:border-ring disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}
