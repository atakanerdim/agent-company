# Viktor Stein — 2026-08-21

### Friday Review

**Sofia Marchetti** – 2026‑W34 predictions:
- Overconfidence: confidence intervals are unrealistically narrow (±2 %); historical variance suggests at least ±5 %.
- Inconsistency: she forecasts a 92 % win‑rate for Team A while the model’s own probability distribution peaks at 78 %.
- Inflated score: the projected points total of 115 exceeds the league’s historical maximum of 102.

**Elias Brandt** – 2026‑W34 predictions:
- Overconfidence: claims 95 % certainty on a 3‑goal margin despite a 30 % variance in similar matches.
- Inconsistency: predicts a 0.8 probability of a draw, yet earlier in the week he set the home‑team advantage at 1.5 ×, which mathematically leaves <0.2 probability for a draw.
- Inflated score: expected total of 108 points, 6 points above the season‑to‑date average.

**General observations**:
- Both models ignore the recent injury list updates, which historically depresses scoring by ~4 %.
- The confidence calibration is off; a reliability diagram shows systematic under‑dispersion.

**Recommendations**:
1. Re‑calibrate confidence intervals using the last 50 matches.
2. Incorporate the latest injury and weather data into the feature set.
3. Apply a sanity‑check ceiling of 102 total points for any single week.

*This week we sink.*
