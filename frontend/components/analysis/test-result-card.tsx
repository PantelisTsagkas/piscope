import type { TestResult } from "@/lib/api/types";
import { formatInteger, formatPValue, formatStatistic } from "@/lib/format";

function Metric({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="flex min-w-0 flex-col gap-0.5">
      <dt className="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
        {label}
      </dt>
      <dd className="font-mono text-sm tabular-nums">{value}</dd>
      {hint ? <dd className="text-[11px] leading-snug text-muted-foreground">{hint}</dd> : null}
    </div>
  );
}

/**
 * One statistical result with everything needed to read it honestly: the statistic, what
 * was expected, the p-value (never presented as the probability of a hypothesis), the
 * sample size, and the assumptions and limitations reported by the engine.
 */
export function TestResultCard({
  result,
  children,
}: {
  result: TestResult;
  children?: React.ReactNode;
}) {
  const descriptive = result.p_value === null || result.p_value === undefined;
  const adjusted = result.adjusted_p_value !== null && result.adjusted_p_value !== undefined;
  return (
    <article
      className="flex min-w-0 flex-col gap-4 border bg-card p-4"
      data-testid={`test-result-${result.key}`}
      aria-label={result.name}
    >
      <header className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-mono text-sm font-medium">{result.name}</h3>
        <span className="border px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground">
          {descriptive ? "descriptive measure" : "hypothesis test"}
        </span>
      </header>

      <dl className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3 xl:grid-cols-5">
        <Metric
          label={`Observed ${result.statistic_name}`}
          value={formatStatistic(result.statistic)}
        />
        <Metric
          label="Expected"
          value={
            result.expected_statistic === null || result.expected_statistic === undefined
              ? "n/a"
              : formatStatistic(result.expected_statistic)
          }
          hint={result.expected_description}
        />
        <Metric
          label="p-value"
          value={formatPValue(result.p_value)}
          hint={descriptive ? "No p-value: this is a description, not a test." : undefined}
        />
        <Metric
          label="Adjusted p-value"
          value={formatPValue(result.adjusted_p_value)}
          hint={
            descriptive
              ? undefined
              : adjusted
                ? "Corrected for the tests in this run."
                : "Single test, so nothing to correct for here."
          }
        />
        <Metric
          label="Sample size"
          value={formatInteger(result.sample_size)}
          hint={
            result.degrees_of_freedom === null || result.degrees_of_freedom === undefined
              ? undefined
              : `${formatInteger(result.degrees_of_freedom)} degrees of freedom`
          }
        />
      </dl>

      <p className="text-sm leading-relaxed" data-testid="test-interpretation">
        {result.interpretation}
      </p>

      {children}

      <details className="text-xs">
        <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
          Null model, assumptions and limitations
        </summary>
        <div className="mt-3 flex flex-col gap-3 text-muted-foreground">
          <p>
            <span className="font-mono text-foreground">Null model: </span>
            {result.null_hypothesis}
          </p>
          <div>
            <span className="font-mono text-foreground">Assumptions</span>
            <ul className="mt-1 list-disc space-y-1 pl-5">
              {result.assumptions.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
          <div>
            <span className="font-mono text-foreground">Limitations</span>
            <ul className="mt-1 list-disc space-y-1 pl-5">
              {result.limitations.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        </div>
      </details>
    </article>
  );
}
