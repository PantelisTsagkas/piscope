# Mathematics and limitations

PiScope computes statistics on a finite prefix of the decimal expansion of pi. This page
explains what those statistics mean and, just as importantly, what they cannot show.

## The short version

- The normality of pi, in base 10 or any other base, **has not been proven**.
- Published statistical studies of the digits of pi, some covering trillions of digits,
  have found nothing inconsistent with normality. That is empirical evidence about the
  digits examined, not a proof about all of them.
- Passing randomness tests does not make a sequence random. The digits of pi are fully
  determined; "random" here only ever means "statistically indistinguishable from a random
  sequence on the measures tested".
- Any finite sequence of digits is expected to appear somewhere in a normal number. Finding
  your birthday, a phone number or a "message" in pi is what the conjecture predicts, and
  carries no meaning.

## Normal numbers

A real number is **simply normal in base b** if each of the b digits appears with limiting
frequency 1/b in its base-b expansion. It is **normal in base b** if, for every length k,
each of the b^k possible blocks of k digits appears with limiting frequency 1/b^k. It is
**absolutely normal** if it is normal in every base.

Borel showed in 1909 that almost every real number (all except a set of measure zero) is
absolutely normal. Despite that, proving normality for a specific, naturally occurring
constant is extremely hard. Constructed examples exist, such as Champernowne's constant
0.123456789101112..., which is normal in base 10 by design.

## The conjecture for pi

It is conjectured that pi is absolutely normal. Nothing close to a proof is known. It has
not even been proven that every decimal digit occurs infinitely often in pi, although no
one seriously doubts it. Computations to trillions of digits show digit and block
frequencies behaving as normality predicts.

A consequence worth stating plainly: normality is a statement about a limit over
infinitely many digits. No finite computation can prove it, and a finite computation could
disprove it only by showing a deviation that grows without bound, which finite data also
cannot do. PiScope can describe a prefix. It cannot settle the question.

## Expected digit frequencies

Under the model "digits are independent and uniform on 0-9", a sample of n digits has an
expected count of n/10 for each digit, with standard deviation sqrt(n x 0.1 x 0.9). For
n = 1,000,000 that is 100,000 with a standard deviation of 300. Individual digits
routinely sit one or two standard deviations away from the expected count, and the largest
deviation among ten digits is usually between 1 and 2.5.

Relative deviation shrinks like 1/sqrt(n) while absolute deviation grows like sqrt(n). A
digit being "ahead" by 242 after a million digits is unremarkable, and the lead is not
expected to shrink in absolute terms.

For a specific sequence of k digits in a range of n digits there are n - k + 1 windows,
each matching with probability 10^-k, so the expected number of occurrences is
(n - k + 1) / 10^k. A given six-digit sequence is expected about once per million digits;
finding one, or none, or three, is ordinary.

## Chi-square goodness of fit

The statistic is

    X^2 = sum over cells of (observed - expected)^2 / expected

For ten digits it has 9 degrees of freedom. If the null model holds, X^2 follows
approximately a chi-square distribution whose mean equals its degrees of freedom. The
p-value is the probability, under the null model, of a statistic at least as large as the
one observed.

Requirements: independent observations and an expected count of at least about 5 per cell.
PiScope flags results where the second condition fails.

**Overlapping n-grams are not independent.** The windows at positions i and i+1 share
n - 1 digits. Applying Pearson's chi-square to overlapping n-gram counts gives a statistic
that does not follow the chi-square distribution, and p-values computed from it are wrong.
PiScope's n-gram test therefore cuts the sequence into non-overlapping blocks. The n-gram
table can still show overlapping counts, because they are the natural description, but
they are labelled as descriptive and their z-scores as approximate.

A very *large* p-value (say above 0.99) is also informative: a fit that is too good is as
unexpected under the model as one that is too poor.

## Shannon entropy

For digit probabilities p_0 to p_9,

    H = - sum of p_i x log2(p_i)   bits per digit

The maximum, reached when all ten digits are equally frequent, is log2(10), about 3.321928
bits. PiScope reports the plug-in estimate from observed frequencies. This estimate is
biased slightly low in finite samples, by about (k - 1) / (2 n ln 2) bits for k = 10
symbols, and that expected value is shown next to the observed one.

Entropy here is a description, not a test, so it has no p-value. It measures only how
balanced the single-digit frequencies are. The sequence 0123456789 repeated forever reaches
the maximum exactly while being as predictable as a sequence can be. High first-order
entropy says nothing about order or dependence.

## Autocorrelation

Treating digits as numbers x_1 to x_n with mean m, the sample autocorrelation at lag k is

    r_k = sum of (x_i - m)(x_(i+k) - m) / sum of (x_i - m)^2

For independent digits, each r_k is approximately normal with mean close to 0 and standard
deviation 1/sqrt(n). PiScope reports each lag with a z-score and p-value, and a single
joint test over all requested lags, the Ljung-Box statistic

    Q = n (n + 2) x sum over k of r_k^2 / (n - k)

which is approximately chi-square with as many degrees of freedom as lags.

Looking at 20 lags is 20 tests. The largest of them will often fall outside the single-lag
95% band by chance alone. Per-lag p-values are therefore also shown with a Holm correction,
and the joint test should be preferred over picking the most extreme lag. Autocorrelation
detects linear dependence between digit values only.

## Runs test

The Wald-Wolfowitz runs test recodes the sequence into two symbols and counts runs, maximal
blocks of the same symbol. PiScope offers two recodings and states which was used: digits
5-9 against 0-4, or odd against even. With n1 and n2 symbols of each kind and n = n1 + n2,

    expected runs = 2 n1 n2 / n + 1
    variance      = 2 n1 n2 (2 n1 n2 - n) / (n^2 (n - 1))

and the standardised count is approximately normal. Too few runs indicate clustering, too
many indicate alternation. The recoding discards most of the information in the digits, so
the test is weak against many kinds of structure.

## Statistical significance

A p-value is the probability of data at least as extreme as what was observed, **computed
assuming the null model is true**. It is not:

- the probability that the null model is true,
- the probability that the result is due to chance,
- the probability that pi is, or is not, normal.

A small p-value means the data would be unusual under the model. A large one means the data
are compatible with it, which is different from confirming it. PiScope's wording follows
this: it reports how often a result this extreme would be expected under the model and
never states a probability for a hypothesis.

If the null model holds, p-values are uniformly distributed between 0 and 1. A p-value
below 0.05 occurs in 5% of honest tests on truly random data. The project's test suite
checks this calibration for every test on simulated sequences.

## Multiple hypothesis testing

Run 20 independent tests on random data and the chance that at least one gives p < 0.05 is
1 - 0.95^20, about 64%. Exploration multiplies tests quickly: different ranges, lags,
n-gram lengths, patterns, window sizes. This is sometimes called the garden of forking
paths, and it is the main way to fool yourself with a tool like this one.

PiScope does three things about it:

1. P-values from one request are adjusted together. The default is the Holm step-down
   method, which controls the family-wise error rate under any dependence between tests and
   is never less powerful than Bonferroni (multiply each p-value by the number of tests).
2. Views with many cells, such as the window heatmap, show how many extreme cells chance
   alone would produce (about 4.55% beyond 2 standard deviations, 0.27% beyond 3) next to
   the number observed.
3. Results carry a reminder that corrections cover a single request. PiScope cannot know
   how many other requests you made before finding something that looks interesting.

**Exploratory versus confirmatory.** Looking through the digits for anything unusual is
exploration. Whatever it turns up is a hypothesis, and its p-value is not interpretable,
because the test was chosen after seeing the data. A confirmatory test fixes the question,
the statistic and the range in advance, and runs once on digits not used in the
exploration. To check an exploratory finding in PiScope, write down the exact test, then
run it on a different range, or expand the dataset and test only the new digits.

## Comparison with simulated sequences

The comparison view generates pseudo-random digit sequences (NumPy PCG64, seeded, with the
seed, bit generator and NumPy version recorded) of the same length as the chosen range and
runs the same tests on them. It reports where pi's statistic falls among the simulated
values.

This shows the natural spread of each statistic, which is often more persuasive than a
formula. It is a descriptive comparison: with 20 simulations, an empirical percentile has a
resolution of 5%. Agreement means that pi cannot be told apart from pseudo-random digits on
those measures in that range. It does not mean that pi is random, and a pseudo-random
generator is itself a deterministic algorithm.

## Limits of finite observation

- A finite prefix says nothing rigorous about the rest of the expansion.
- Statistical tests examine specific properties. A sequence can pass every test in a
  battery and still have structure the battery does not look for. The digits of pi are, in
  fact, computable by a short program, which is the opposite of algorithmically random.
- Absence of evidence against normality accumulates with more digits and more tests, and
  makes the conjecture more plausible to mathematicians, but plausibility is not proof.
- Striking finds in the data are expected. The six consecutive 9s starting at decimal
  position 762 look remarkable. Under a random model about nine runs of six or more
  identical digits are expected per million digits (n x 0.81 x 0.1^5 for length six alone
  is 8.1), so the run itself is ordinary. Seeing one that early is less common, roughly
  0.7% for the first 762 positions (762 x 0.9 x 10^-5), but it was singled out after the fact from countless
  curiosities that could have been noticed instead, which is exactly the situation the
  multiple-testing section warns about. PiScope shows the expected count next to the
  observed one for this reason.

## Further reading

- E. Borel, "Les probabilités dénombrables et leurs applications arithmétiques" (1909).
- D. H. Bailey, J. M. Borwein, C. S. Calude, M. J. Dinneen, M. Dumitrescu, A. Yee, "An
  empirical approach to the normality of pi", Experimental Mathematics 21 (2012).
- D. Knuth, The Art of Computer Programming, volume 2, section 3.3 (statistical tests).
- S. Holm, "A simple sequentially rejective multiple test procedure", Scandinavian Journal
  of Statistics 6 (1979).
- G. M. Ljung and G. E. P. Box, "On a measure of lack of fit in time series models",
  Biometrika 65 (1978).
