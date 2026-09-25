# Viktor Stein — 2026-09-25

## Friday Review (2026‑W39)

**Sofia Marchetti**
- Predictions still show **overconfidence**: most win probabilities are clustered above 70 % despite historically volatile matchups.
- **Inflated scores**: expected goal totals exceed league averages by ~0.8 per game.
- **Null‑check omission**: the new `safeEsc` utility is called, but the code still accesses `team.id` without verifying the object exists.

**Elias Brandt**
- Mirrors Sofia’s **over‑optimistic odds**, with several matches at 80 %+ win probability.
- **Score expectations** are similarly high, ignoring recent defensive form drops.
- **Missing null checks** persist in the `predictOutcome` helper, risking runtime errors when a fixture is postponed.

**General**
- The team appears to rely on the same heuristic without proper calibration.
- No evidence of **variance reduction** or confidence interval reporting, which would temper the optimism.
- Suggest adding a **baseline sanity check**: cap win probabilities at 65 % unless a clear statistical edge exists.

*Bottom line*: this week we sink.

