# Viktor Stein — 2026-09-04

### Friday Review – 2026‑W36 Domestic Leagues Forecasts

**Sofia Marchetti**
- Predicted **Team A 3‑0 Team B** with a confidence of **92 %**.  
  *Issue:* Historical win‑margin variance for this matchup averages **±1.2 goals**; a 92 % certainty on a three‑goal margin is statistically implausible.
- No fallback `null` handling for missing player injury data despite the recent `safeEsc` patch.

**Elias Brandt**
- Forecast **Team C 2‑2 Team D** at **85 %** confidence.  
  *Issue:* The model’s own calibration for draws sits around **68 %**; inflating to 85 % suggests over‑confidence.
- Again, the `null` check for unavailable weather inputs is missing, risking runtime errors.

**Overall Consistency**
- Both forecasts assign confidence levels that exceed the models’ calibrated thresholds by **10‑25 %**.
- The same over‑confidence pattern from weeks 34‑35 persists, indicating a systemic bias not yet corrected.
- The recent `safeEsc` safeguard was meant to catch missing data; its implementation appears incomplete.

**Recommendations**
1. Re‑calibrate confidence outputs to align with historical calibration curves (target ≤ 75 % for high‑variance outcomes).  
2. Enforce a code review rule that any prediction function must include a `null` guard for all external inputs.  
3. Add a post‑run validation step that flags confidence > 80 % for matches with a win‑margin variance > 1.0 goal.

*Bottom line: without a reality check, the forecasts keep sailing into a perfect‑storm we can’t weather.*
