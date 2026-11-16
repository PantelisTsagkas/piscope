"use client";

import { Field, NativeSelect } from "@/components/shared/field";
import { Input } from "@/components/ui/input";
import { TEST_KEYS, TEST_LABELS, type TestKey } from "@/lib/api/types";
import { formatInteger } from "@/lib/format";
import { parsePositiveInteger } from "@/lib/params";

export interface TestOptionValues {
  tests: TestKey[];
  maxLag: string;
  ngramLength: string;
  runsDichotomy: "high_low" | "parity";
}

export interface TestOptionLimits {
  maxLag: number;
  maxNgramLength: number;
}

/** Validation messages for the shared test options; all null when the options are valid. */
export function validateTestOptions(values: TestOptionValues, limits: TestOptionLimits) {
  const lag = parsePositiveInteger(values.maxLag);
  const ngram = parsePositiveInteger(values.ngramLength);
  return {
    tests: values.tests.length === 0 ? "Select at least one test." : null,
    maxLag:
      lag === null
        ? "Enter a whole number of 1 or more."
        : lag > limits.maxLag
          ? `At most ${formatInteger(limits.maxLag)}.`
          : null,
    ngramLength:
      ngram === null
        ? "Enter a whole number of 1 or more."
        : ngram > limits.maxNgramLength
          ? `At most ${limits.maxNgramLength}.`
          : null,
  };
}

export function parseTestKeys(text: string | null): TestKey[] {
  if (!text) return [...TEST_KEYS];
  const requested = text.split(",");
  const keys = TEST_KEYS.filter((key) => requested.includes(key));
  return keys.length > 0 ? keys : [...TEST_KEYS];
}

/** Test selection and the parameters that only some tests use. */
export function TestOptions({
  idPrefix,
  values,
  limits,
  onChange,
}: {
  idPrefix: string;
  values: TestOptionValues;
  limits: TestOptionLimits;
  onChange: (values: TestOptionValues) => void;
}) {
  const errors = validateTestOptions(values, limits);
  const uses = (key: TestKey) => values.tests.includes(key);

  return (
    <>
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1.5 font-mono text-[11px] tracking-wider uppercase">Tests</legend>
        <div className="flex flex-wrap gap-x-5 gap-y-2">
          {TEST_KEYS.map((key) => (
            <label key={key} className="flex cursor-pointer items-center gap-2 text-sm">
              <input
                type="checkbox"
                className="size-4 accent-primary"
                checked={uses(key)}
                onChange={(event) =>
                  onChange({
                    ...values,
                    tests: event.target.checked
                      ? TEST_KEYS.filter((item) => item === key || uses(item))
                      : values.tests.filter((item) => item !== key),
                  })
                }
              />
              {TEST_LABELS[key]}
            </label>
          ))}
        </div>
        {errors.tests ? (
          <p role="alert" className="text-xs text-destructive">
            {errors.tests}
          </p>
        ) : null}
      </fieldset>

      <div className="flex flex-wrap items-start gap-3">
        <Field
          id={`${idPrefix}-max-lag`}
          label="Largest lag"
          hint="Autocorrelation"
          error={uses("autocorrelation") ? errors.maxLag : null}
          className="w-36"
        >
          <Input
            id={`${idPrefix}-max-lag`}
            inputMode="numeric"
            value={values.maxLag}
            disabled={!uses("autocorrelation")}
            onChange={(event) => onChange({ ...values, maxLag: event.target.value })}
            className="font-mono"
          />
        </Field>
        <Field
          id={`${idPrefix}-ngram-length`}
          label="Block length"
          hint="N-gram block test"
          error={uses("ngram_blocks") ? errors.ngramLength : null}
          className="w-36"
        >
          <Input
            id={`${idPrefix}-ngram-length`}
            inputMode="numeric"
            value={values.ngramLength}
            disabled={!uses("ngram_blocks")}
            onChange={(event) => onChange({ ...values, ngramLength: event.target.value })}
            className="font-mono"
          />
        </Field>
        <Field id={`${idPrefix}-dichotomy`} label="Runs split" hint="Runs test" className="w-56">
          <NativeSelect
            id={`${idPrefix}-dichotomy`}
            value={values.runsDichotomy}
            disabled={!uses("runs")}
            onChange={(event) =>
              onChange({ ...values, runsDichotomy: event.target.value as "high_low" | "parity" })
            }
          >
            <option value="high_low">Low (0-4) and high (5-9)</option>
            <option value="parity">Even and odd</option>
          </NativeSelect>
        </Field>
      </div>
    </>
  );
}

/** True when the shared options have no validation errors for the selected tests. */
export function testOptionsValid(values: TestOptionValues, limits: TestOptionLimits): boolean {
  const errors = validateTestOptions(values, limits);
  if (errors.tests) return false;
  if (values.tests.includes("autocorrelation") && errors.maxLag) return false;
  if (values.tests.includes("ngram_blocks") && errors.ngramLength) return false;
  return true;
}
