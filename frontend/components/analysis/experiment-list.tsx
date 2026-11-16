import { FlaskConical, Scale, Search, Sigma, type LucideIcon } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import type { Experiment } from "@/lib/api/types";
import { formatInteger, formatPValue, formatTimestamp } from "@/lib/format";

const KIND_ICONS: Record<string, LucideIcon> = {
  search: Search,
  statistics: Sigma,
  comparison: Scale,
};

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

/** A link that reopens the page with the experiment's recorded parameters. */
export function repeatHref(experiment: Experiment): string | null {
  const p = experiment.parameters;
  const params = new URLSearchParams();
  const set = (key: string, value: unknown) => {
    if (typeof value === "string" || typeof value === "number") params.set(key, String(value));
  };
  if (experiment.kind === "search") {
    set("q", p.pattern);
    set("start", p.start);
    set("end", p.end);
    return `/search?${params.toString()}`;
  }
  if (experiment.kind === "statistics" || experiment.kind === "comparison") {
    params.set("tab", experiment.kind === "statistics" ? "tests" : "compare");
    set("start", p.start);
    set("count", p.count);
    set("max_lag", p.max_lag);
    set("ngram_length", p.ngram_length);
    set("runs_dichotomy", p.runs_dichotomy);
    if (Array.isArray(p.tests)) params.set("tests", p.tests.join(","));
    if (experiment.kind === "statistics") set("correction", p.correction);
    else {
      set("seed", p.seed);
      set("simulations", p.simulations);
    }
    return `/lab?${params.toString()}`;
  }
  return null;
}

/** One line describing the headline result of an experiment, from its recorded summary. */
export function summarize(experiment: Experiment): string {
  const summary = experiment.summary;
  if (experiment.kind === "search") {
    const total = asNumber(summary.total_count);
    const first = asNumber(summary.first_position);
    if (total === null) return "";
    if (total === 0) return "No occurrences";
    return `${formatInteger(total)} occurrence${total === 1 ? "" : "s"}${
      first !== null ? `, first at position ${formatInteger(first)}` : ""
    }`;
  }
  if (experiment.kind === "statistics") {
    const adjusted = Object.values(asRecord(summary.adjusted_p_values))
      .map(asNumber)
      .filter((value): value is number => value !== null);
    if (adjusted.length === 0) return "Descriptive measures only";
    return `${adjusted.length} test${adjusted.length === 1 ? "" : "s"}, smallest adjusted p ${formatPValue(Math.min(...adjusted))}`;
  }
  if (experiment.kind === "comparison") {
    const seed = asNumber(experiment.parameters.seed);
    const simulations = asNumber(experiment.parameters.simulations);
    return `${simulations ?? "?"} simulation${simulations === 1 ? "" : "s"}, seed ${seed ?? "?"}`;
  }
  return "";
}

export function ExperimentList({
  experiments,
  compact = false,
}: {
  experiments: Experiment[];
  compact?: boolean;
}) {
  return (
    <ul className="flex flex-col divide-y border" data-testid="experiment-list">
      {experiments.map((experiment) => {
        const Icon = KIND_ICONS[experiment.kind] ?? FlaskConical;
        const href = repeatHref(experiment);
        return (
          <li key={experiment.id} className="flex flex-col gap-2 p-3">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <Icon aria-hidden className="size-4 shrink-0 text-cyan" />
              <span className="min-w-0 flex-1 font-mono text-[13px] break-words">
                {experiment.title}
              </span>
              <Badge variant="outline" className="font-mono">
                {experiment.kind}
              </Badge>
            </div>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 pl-7 text-xs text-muted-foreground">
              <time dateTime={experiment.timestamp}>{formatTimestamp(experiment.timestamp)}</time>
              <span>{summarize(experiment)}</span>
              {href ? (
                <Link href={href} className="text-primary underline-offset-4 hover:underline">
                  Repeat
                </Link>
              ) : null}
            </div>
            {compact ? null : (
              <details className="pl-7 text-xs">
                <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                  Parameters and recorded results
                </summary>
                <pre className="mt-2 overflow-x-auto border bg-background p-3 font-mono text-[11px] leading-relaxed">
                  {JSON.stringify(
                    { parameters: experiment.parameters, summary: experiment.summary },
                    null,
                    2,
                  )}
                </pre>
              </details>
            )}
          </li>
        );
      })}
    </ul>
  );
}
