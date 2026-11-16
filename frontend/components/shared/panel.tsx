import { cn } from "@/lib/utils";

/** A titled section. Every analysis block on a page is one of these. */
export function Panel({
  title,
  description,
  action,
  children,
  className,
  ...props
}: {
  title: string;
  description?: React.ReactNode;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
} & Omit<React.ComponentProps<"section">, "title">) {
  return (
    <section className={cn("flex min-w-0 flex-col border bg-card", className)} {...props}>
      <header className="flex flex-wrap items-start justify-between gap-3 border-b px-4 py-3">
        <div className="flex min-w-0 flex-col gap-1">
          <h2 className="font-mono text-sm font-medium">{title}</h2>
          {description ? <p className="text-xs text-muted-foreground">{description}</p> : null}
        </div>
        {action}
      </header>
      <div className="flex min-w-0 flex-1 flex-col gap-4 p-4">{children}</div>
    </section>
  );
}

/** A single headline number with a label and optional context line. */
export function Stat({
  label,
  value,
  detail,
  accent = "none",
  testId,
}: {
  label: string;
  value: React.ReactNode;
  detail?: React.ReactNode;
  accent?: "none" | "cyan" | "purple" | "blue";
  testId?: string;
}) {
  const bar = { none: "bg-border", cyan: "bg-cyan", purple: "bg-primary", blue: "bg-blue" }[accent];
  return (
    <div className="relative flex min-w-0 flex-col gap-1 border bg-card py-3 pr-4 pl-5">
      <span aria-hidden className={cn("absolute inset-y-0 left-0 w-0.5", bar)} />
      <span className="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
        {label}
      </span>
      <span className="truncate font-mono text-lg font-medium tabular-nums" data-testid={testId}>
        {value}
      </span>
      {detail ? <span className="text-xs text-muted-foreground">{detail}</span> : null}
    </div>
  );
}

/** A caveat or methodological note that must stay visible next to a result. */
export function Note({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <p
      className={cn(
        "border-l-2 border-blue/60 bg-blue/5 px-3 py-2 text-xs leading-relaxed text-muted-foreground",
        className,
      )}
    >
      {children}
    </p>
  );
}
