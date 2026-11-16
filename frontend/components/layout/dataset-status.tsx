"use client";

import { useDatasetInfo } from "@/lib/api/hooks";
import { formatInteger } from "@/lib/format";
import { cn } from "@/lib/utils";

/** Compact dataset indicator shown in the navigation: size when loaded, the problem otherwise. */
export function DatasetStatus({ className }: { className?: string }) {
  const { data, error, isPending } = useDatasetInfo();

  let dot = "bg-muted-foreground";
  let title = "Checking dataset";
  let detail = "Contacting the API";
  if (data) {
    dot = data.has_partial_chunk ? "bg-amber" : "bg-cyan";
    title = `${formatInteger(data.total_digits)} digits`;
    detail = data.checksums_verified_at_startup ? "Checksums verified" : "Checksums not verified";
  } else if (error) {
    dot = "bg-destructive";
    title = error.datasetUnavailable ? "No dataset" : "API unreachable";
    detail = error.datasetUnavailable ? "Generate digits to begin" : "Start the API server";
  }

  return (
    <div
      className={cn("flex items-center gap-2.5 font-mono text-xs", className)}
      role="status"
      aria-live="polite"
      aria-busy={isPending}
      data-testid="dataset-status"
    >
      <span aria-hidden className={cn("size-2 shrink-0", dot)} />
      <span className="flex flex-col leading-tight">
        <span className="text-foreground">{title}</span>
        <span className="text-muted-foreground">{detail}</span>
      </span>
    </div>
  );
}
