# Viktor Stein — 2026-11-27

Viktor Stein, Critic
- **Overconfidence persists**: Sofia and Elias both assign win probabilities >90% for multiple matches, despite comparable team strengths. This inflates expected points and will likely miss the actual variance.
- **Score inflation**: Predicted goal totals average 4.2 per match, a 30% increase over the league’s season average of 3.1. Without a cap, the model will consistently overshoot.
- **Inconsistent scaling**: Sofia uses a 0‑100 confidence scale while Elias uses 0‑1 decimals; the aggregation script treats them uniformly, causing double‑weighting of Sofia’s values.
- **Missing null checks**: The new `safeEsc` helper is called on `match.id` without verifying the field exists; any missing ID will raise an exception and abort the batch.
- **Recommendation**: Introduce a max confidence of 85%, normalize both scales to a 0‑1 range before merging, and add a guard `if (match.id) { … }` around `safeEsc` calls.
