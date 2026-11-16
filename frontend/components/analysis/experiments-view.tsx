"use client";

import { Trash2 } from "lucide-react";
import { useState } from "react";

import { Field, NativeSelect } from "@/components/shared/field";
import { PageHeader } from "@/components/shared/page-header";
import { Note, Panel } from "@/components/shared/panel";
import { EmptyState, ErrorState, RowsSkeleton } from "@/components/shared/states";
import { Button } from "@/components/ui/button";
import { useClearExperiments, useExperiments } from "@/lib/api/hooks";

import { ExperimentList } from "./experiment-list";

const KINDS = [
  { value: "", label: "All kinds" },
  { value: "search", label: "Searches" },
  { value: "statistics", label: "Test batteries" },
  { value: "comparison", label: "Random comparisons" },
];
/** The API returns at most this many experiments per request. */
const LOG_LIMIT = 100;

export function ExperimentsView() {
  const [kind, setKind] = useState("");
  const [confirming, setConfirming] = useState(false);
  const experiments = useExperiments(LOG_LIMIT, kind || null);
  const clear = useClearExperiments();
  const items = experiments.data?.experiments ?? [];

  return (
    <>
      <PageHeader
        title="Experiments"
        description="A log of the searches, test runs and comparisons made through this server, with the parameters needed to repeat each one."
      />
      <Note>
        The log is also a record of how much you have explored. The more ranges and settings you
        try, the more likely it is that something looks unusual by chance.
      </Note>

      <Panel
        title="Log"
        description={
          experiments.data
            ? `${items.length} experiment${items.length === 1 ? "" : "s"} shown, newest first.`
            : "Loading experiments"
        }
        action={
          <div className="flex flex-wrap items-end gap-3">
            <Field id="experiment-kind" label="Kind" className="w-48">
              <NativeSelect
                id="experiment-kind"
                value={kind}
                onChange={(event) => setKind(event.target.value)}
              >
                {KINDS.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </NativeSelect>
            </Field>
            {confirming ? (
              <div
                className="flex items-center gap-2"
                role="group"
                aria-label="Confirm clearing the log"
              >
                <span className="text-xs text-muted-foreground">Delete every experiment?</span>
                <Button
                  variant="destructive"
                  disabled={clear.isPending}
                  onClick={() => clear.mutate(undefined, { onSettled: () => setConfirming(false) })}
                >
                  {clear.isPending ? "Deleting" : "Delete all"}
                </Button>
                <Button variant="outline" onClick={() => setConfirming(false)}>
                  Cancel
                </Button>
              </div>
            ) : (
              <Button
                variant="outline"
                disabled={items.length === 0}
                onClick={() => setConfirming(true)}
              >
                <Trash2 aria-hidden /> Clear log
              </Button>
            )}
          </div>
        }
      >
        {clear.error ? <ErrorState error={clear.error} /> : null}
        {experiments.error ? (
          <ErrorState error={experiments.error} onRetry={() => void experiments.refetch()} />
        ) : !experiments.data ? (
          <RowsSkeleton rows={5} />
        ) : items.length === 0 ? (
          <EmptyState title={kind ? "No experiments of this kind" : "No experiments yet"}>
            <p>
              Searches, test batteries and random comparisons are recorded here as you run them.
            </p>
          </EmptyState>
        ) : (
          <ExperimentList experiments={items} />
        )}
      </Panel>
    </>
  );
}
