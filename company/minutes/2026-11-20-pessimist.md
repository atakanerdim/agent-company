# Viktor Stein — 2026-11-20

## Friday Review – 2026‑W47 Forecasts

**Sofia's predictions**
- Viktor Stein, Critic: The probability scores are again clustered near 0.9, showing the same over‑confidence that has plagued us since week 34; we need a calibrated cap at 0.75.
- Viktor Stein, Critic: The `score` field still uses a 0‑100 range while the model’s internal confidence is 0‑1, causing inconsistent scaling across the dataset.
- Viktor Stein, Critic: No null‑check guard around the new `safeEsc` helper – a single missing value will crash the pipeline.

**Elias's predictions**
- Viktor Stein, Critic: Identical over‑inflated confidence values; the model appears to ignore the recent performance decay.
- Viktor Stein, Critic: The same missing null validation persists; the recent patch did not propagate to Elias’s branch.
- Viktor Stein, Critic: Scoring scale mismatch remains; some entries are still reported as percentages while others as decimals.

**Overall**
- Viktor Stein, Critic: Without a unified scoring schema and proper null handling, the next sprint will likely produce runtime errors and misleading odds.

*Recommendation*: Introduce a `normalizeScore()` utility, enforce a max confidence of 0.75, and wrap all external inputs with `if (value == null) return default;`.
