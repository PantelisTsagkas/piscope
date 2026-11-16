"use client";

import { PageHeader } from "@/components/shared/page-header";
import { Panel } from "@/components/shared/panel";
import { ErrorState, RowsSkeleton } from "@/components/shared/states";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { API_BASE } from "@/lib/api/client";
import { useDatasetInfo } from "@/lib/api/hooks";
import { formatInteger, formatTimestamp } from "@/lib/format";

const LIMIT_LABELS: Record<string, string> = {
  max_range_digits: "Digits per explorer page",
  max_pattern_length: "Search sequence length",
  search_max_limit: "Matches per search page",
  max_analysis_digits: "Digits per frequency count",
  max_statistics_digits: "Digits per n-gram, test, window or run analysis",
  max_ngram_length: "Largest n-gram length",
  max_autocorrelation_lag: "Largest autocorrelation lag",
  max_random_digits: "Digits per simulated sequence",
  max_simulations: "Simulated sequences per comparison",
  max_simulated_total_digits: "Simulated digits per comparison, all sequences",
  max_windows: "Windows per concentration analysis",
};

export function AboutView() {
  const dataset = useDatasetInfo();
  const info = dataset.data;

  return (
    <>
      <PageHeader
        title="About"
        description="What PiScope measures, where its digits come from, and what its results can and cannot tell you."
      />

      <Panel title="What the results mean">
        <div className="flex max-w-3xl flex-col gap-3 text-sm leading-relaxed">
          <p>
            A number is <strong>normal</strong> in base 10 if every sequence of digits of a given
            length occurs equally often in the long run. Pi is widely believed to be normal, and
            every large computation so far is consistent with that, but it{" "}
            <strong>has not been proven</strong>. It is not even known whether each digit occurs
            infinitely often.
          </p>
          <p>
            PiScope analyses a finite prefix of pi. Its tests ask whether that prefix looks like
            digits drawn independently with equal probability. A result compatible with that model
            means only that this test found no departure in this range. It does not establish
            normality or randomness, and pi&apos;s digits are not random: they are fixed and
            computable.
          </p>
          <p>
            A p-value is the probability, if the model were true, of a statistic at least as extreme
            as the one observed. It is not the probability that the model is true or false. When
            many ranges, sequences and tests are tried, some small p-values and striking
            coincidences are certain to appear. Treat anything found by browsing as a hypothesis to
            check on digits you have not yet looked at.
          </p>
          <p>
            Any short sequence, including dates and phone numbers, is expected to appear somewhere
            in a long run of digits. Finding one is not evidence of a hidden message.
          </p>
        </div>
      </Panel>

      <Panel title="Position convention">
        <div className="flex max-w-3xl flex-col gap-3 text-sm leading-relaxed">
          <p>
            Position 1 is the first digit after the decimal point. In{" "}
            <span className="font-mono">
              3.<span className="bg-primary px-0.5 text-primary-foreground">1</span>4159
            </span>{" "}
            the highlighted 1 is at position 1 and the 4 is at position 2. The integer digit 3 is
            not stored and has no position. Every page and every API field uses this convention.
          </p>
          {info ? (
            <p className="font-mono text-xs text-muted-foreground" data-testid="about-indexing">
              Dataset record: {info.indexing}
            </p>
          ) : null}
        </div>
      </Panel>

      {dataset.error ? (
        <ErrorState error={dataset.error} onRetry={() => void dataset.refetch()} />
      ) : !info ? (
        <Panel title="Dataset provenance" description="Loading dataset">
          <RowsSkeleton rows={6} />
        </Panel>
      ) : (
        <>
          <Panel
            title="Dataset provenance"
            description="Read from the dataset manifest. Digits are stored only after they pass verification."
          >
            <dl
              className="grid gap-x-8 gap-y-3 text-sm sm:grid-cols-2 xl:grid-cols-3"
              data-testid="about-provenance"
            >
              <Fact label="Digits stored" value={formatInteger(info.total_digits)} />
              <Fact
                label="Completeness"
                value={
                  info.has_partial_chunk
                    ? "Final chunk is partial"
                    : `${info.chunk_count} complete chunk${info.chunk_count === 1 ? "" : "s"}`
                }
              />
              <Fact
                label="Checksums at startup"
                value={info.checksums_verified_at_startup ? "Verified" : "Not verified"}
              />
              <Fact label="Encoding" value={info.encoding} />
              <Fact label="Created" value={formatTimestamp(info.created_at)} />
              <Fact label="Last updated" value={formatTimestamp(info.updated_at)} />
              {Object.entries(info.generator).map(([key, value]) => (
                <Fact
                  key={key}
                  label={`Generator: ${key.replaceAll("_", " ")}`}
                  value={String(value)}
                />
              ))}
            </dl>

            <h3 className="font-mono text-xs text-muted-foreground uppercase">
              Independent verification
            </h3>
            {info.verifications.length === 0 ? (
              <p className="text-sm text-destructive">
                No verification is recorded for this dataset. Treat its digits as unverified.
              </p>
            ) : (
              <ul className="flex flex-col gap-2">
                {info.verifications.map((item) => (
                  <li key={item.method} className="border p-3 text-sm">
                    <span className="font-mono text-cyan">{item.method}</span>
                    <span className="text-muted-foreground">
                      {" "}
                      , {formatInteger(item.digits_compared)} digits compared
                    </span>
                    <p className="mt-1 text-xs break-words text-muted-foreground">{item.detail}</p>
                  </li>
                ))}
              </ul>
            )}

            <h3 className="font-mono text-xs text-muted-foreground uppercase">Chunks</h3>
            <div className="max-h-72 overflow-y-auto border">
              <Table>
                <TableHeader className="sticky top-0 bg-card">
                  <TableRow>
                    <TableHead className="font-mono">Chunk</TableHead>
                    <TableHead className="text-right font-mono">First position</TableHead>
                    <TableHead className="text-right font-mono">Digits</TableHead>
                    <TableHead className="font-mono">Complete</TableHead>
                    <TableHead className="font-mono">SHA-256</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {info.chunks.map((chunk) => (
                    <TableRow key={chunk.index}>
                      <TableCell className="font-mono tabular-nums">{chunk.index}</TableCell>
                      <TableCell className="text-right font-mono tabular-nums">
                        {formatInteger(chunk.first_position)}
                      </TableCell>
                      <TableCell className="text-right font-mono tabular-nums">
                        {formatInteger(chunk.digit_count)}
                      </TableCell>
                      <TableCell className="font-mono">
                        {chunk.complete ? "yes" : "partial"}
                      </TableCell>
                      <TableCell className="font-mono text-[11px] text-muted-foreground">
                        {chunk.sha256}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </Panel>

          <Panel
            title="Request limits"
            description="Large requests are refused up front instead of being left to time out."
          >
            <dl className="grid gap-x-8 gap-y-3 text-sm sm:grid-cols-2 xl:grid-cols-3">
              {Object.entries(info.limits).map(([key, value]) => (
                <Fact key={key} label={LIMIT_LABELS[key] ?? key} value={formatInteger(value)} />
              ))}
            </dl>
          </Panel>
        </>
      )}

      <Panel title="API">
        <p className="max-w-3xl text-sm leading-relaxed">
          Everything shown in PiScope comes from a versioned REST API that you can call directly.
          Interactive documentation is at{" "}
          <a
            href={`${API_BASE}/docs`}
            className="font-mono text-primary underline-offset-4 hover:underline"
            target="_blank"
            rel="noreferrer"
          >
            {API_BASE}/docs
          </a>
          .
        </p>
      </Panel>
    </>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex min-w-0 flex-col gap-0.5">
      <dt className="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
        {label}
      </dt>
      <dd className="font-mono text-sm break-words">{value}</dd>
    </div>
  );
}
