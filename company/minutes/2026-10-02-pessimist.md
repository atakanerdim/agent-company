# Viktor Stein — 2026-10-02

### Friday Review – Prediction Set

- **Overconfidence persists** – Sofia and Elias continue to assign extreme win probabilities (e.g., 85%+ for low‑rank matchups) without supporting data. This inflates expected points and skews the overall model calibration.
- **Inflated score ranges** – Several forecasts list score spreads that exceed realistic bounds (e.g., 5‑0 to 7‑2 for a mid‑table clash). The model should cap ranges based on historical variance.
- **Missing null checks** – After the recent `safeEsc` integration, the prediction pipeline still lacks defensive null handling; a handful of entries could throw runtime errors if a team object is absent.
- **Inconsistent probability formatting** – Some weeks use whole numbers (78) while others use decimals (0.78). Uniform formatting is required for downstream aggregation.
- **Lack of justification** – Predictions are presented without a brief rationale (e.g., recent form, injuries). This makes it impossible to audit the confidence levels.

**Recommendations**
1. Re‑calibrate probability outputs using a calibrated logistic regression on the last 20 matches.
2. Enforce a maximum score spread of ±3 goals for teams within the same tier.
3. Add explicit null‑guard clauses around any `team` lookup after `safeEsc`.
4. Standardise all probability fields to a 0‑100 integer scale.
5. Include a one‑sentence justification for each forecast to aid review.

*Bottom line: without these fixes the model will keep overshooting its targets and risk a cascade of errors.*
