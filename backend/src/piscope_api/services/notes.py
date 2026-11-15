"""Standard explanatory texts attached to analysis responses."""

FREQUENCY_NOTE = (
    "Expected counts assume each digit is equally likely (1/10). Deviations of a few "
    "standard deviations are normal in any finite sample; the chi-square test in the "
    "Statistical Lab tests the whole distribution at once."
)

NGRAM_NOTE_OVERLAPPING = (
    "Counts use overlapping windows (one per position). Neighbouring windows share digits, "
    "so these counts are not independent and the standardized deviations are approximate, "
    "especially for self-overlapping sequences such as 11 or 121. The attached chi-square "
    "test therefore uses non-overlapping blocks instead."
)

NGRAM_NOTE_DISJOINT = (
    "Counts use non-overlapping blocks, which are independent under a random model. "
    "Leftover digits at the end of the range are ignored."
)

MULTIPLE_TESTING_NOTE = (
    "Each p-value answers one question. Running several tests, or trying several ranges "
    "and settings, makes at least one small p-value likely by chance alone. Adjusted "
    "p-values correct for the tests in this request only; they cannot account for other "
    "requests you have made. Treat anything found by exploring as a hypothesis to check on "
    "digits you have not looked at yet."
)

SCOPE_NOTE = (
    "These results describe a finite range of digits. The normality of pi has not been "
    "proven, and passing statistical tests does not establish randomness or normality."
)

COMPARISON_NOTE = (
    "Simulated sequences come from a pseudo-random generator and show the spread each "
    "statistic has by chance. Pi's digits are fixed, not random; agreement with the "
    "simulations means pi is statistically indistinguishable from them on these measures "
    "in this range, not that pi is random. The percentile is descriptive, not a p-value."
)

WINDOW_NOTE = (
    "Each cell is a z-score for one digit in one window. With many cells, some large "
    "values are expected by chance: about 4.55% of cells beyond 2 and 0.27% beyond 3 under "
    "a random model. Compare the observed number of extreme cells with the expected number "
    "before treating any single window as unusual."
)

RUNS_NOTE = (
    "A run is a maximal block of one repeated digit. Expected counts assume independent "
    "uniform digits: about n x 0.81 x 0.1^(k-1) runs of length k. Long runs are certain to "
    "appear in a long enough random sequence."
)

OBSERVATIONS_CAVEAT = (
    "Computed from the stored digits on request. Observations are descriptive: they report "
    "what this finite range contains and are not evidence of hidden structure in pi."
)
