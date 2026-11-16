import { AlertTriangle, DatabaseZap, Inbox, ServerOff, type LucideIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { API_ORIGIN, ApiError } from "@/lib/api/client";
import { cn } from "@/lib/utils";

function Frame({
  icon: Icon,
  title,
  tone = "muted",
  children,
  className,
  role,
}: {
  icon: LucideIcon;
  title: string;
  tone?: "muted" | "error";
  children?: React.ReactNode;
  className?: string;
  role?: "alert" | "status";
}) {
  return (
    <div
      role={role}
      className={cn(
        "flex flex-col items-start gap-2 border border-dashed p-5 text-sm",
        tone === "error" && "border-destructive/50",
        className,
      )}
    >
      <div className="flex items-center gap-2 font-mono font-medium">
        <Icon
          aria-hidden
          className={cn("size-4", tone === "error" ? "text-destructive" : "text-muted-foreground")}
        />
        {title}
      </div>
      <div className="flex flex-col gap-2 text-muted-foreground">{children}</div>
    </div>
  );
}

/** Shown when there is nothing to display yet and that is not an error. */
export function EmptyState({
  title,
  children,
  className,
}: {
  title: string;
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <Frame icon={Inbox} title={title} className={className} role="status">
      {children}
    </Frame>
  );
}

/** Explains a failed request and, where it helps, how to fix it. */
export function ErrorState({
  error,
  onRetry,
  className,
}: {
  error: unknown;
  onRetry?: () => void;
  className?: string;
}) {
  const retry = onRetry ? (
    <Button variant="outline" size="sm" onClick={onRetry} className="mt-1 self-start">
      Try again
    </Button>
  ) : null;

  if (error instanceof ApiError && error.unreachable) {
    return (
      <Frame
        icon={ServerOff}
        title="The API is not reachable"
        tone="error"
        role="alert"
        className={className}
      >
        <p>
          PiScope could not connect to <code className="font-mono">{API_ORIGIN}</code>. Start it
          with <code className="font-mono">uv run piscope-api</code> and try again.
        </p>
        {retry}
      </Frame>
    );
  }
  if (error instanceof ApiError && error.datasetUnavailable) {
    return (
      <Frame
        icon={DatabaseZap}
        title="No digits are available"
        tone="error"
        role="alert"
        className={className}
      >
        <p>{error.message}</p>
        <p>
          Generate and verify the first million digits with{" "}
          <code className="font-mono">uv run piscope-digits generate</code>, then restart the API.
        </p>
        {retry}
      </Frame>
    );
  }
  const message = error instanceof Error ? error.message : "Unexpected error";
  return (
    <Frame
      icon={AlertTriangle}
      title="The request could not be completed"
      tone="error"
      role="alert"
      className={className}
    >
      <p>{message}</p>
      {retry}
    </Frame>
  );
}

/** Placeholder with the footprint of a chart. */
export function ChartSkeleton({ className }: { className?: string }) {
  return <Skeleton className={cn("h-72 w-full", className)} data-testid="chart-skeleton" />;
}

export function RowsSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="flex flex-col gap-2" aria-hidden>
      {Array.from({ length: rows }, (_, index) => (
        <Skeleton key={index} className="h-6 w-full" />
      ))}
    </div>
  );
}

/** Suspense fallback for a whole page. */
export function PageSkeleton() {
  return (
    <div className="flex flex-col gap-6" role="status" aria-label="Loading page">
      <div className="flex flex-col gap-2">
        <Skeleton className="h-7 w-56" />
        <Skeleton className="h-4 w-96 max-w-full" />
      </div>
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-72 w-full" />
    </div>
  );
}
