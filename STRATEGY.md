# Strategy

Forecast GTA VI's launch-day Twitch viewers (hours 2..24) from hour 1's
print and the 38 comparable past launches in the case file.

## Core idea

Launch-day viewership follows a characteristic shape once you divide by
the first hour: a dip in the small hours, a jump at US midnight
(04:00–05:00Z, rolling midnight unlock), a climb to a late-afternoon peak,
then decay. That shape is stable across big launches, but its amplitude
and timing depend on the launch — so instead of assuming one shape, we
average the log-ratio curves `ln(viewers_h / viewers_1)` of past launches,
weighted by how similar each launch is to the target.

## Similarity kernel (per comparable)

- **Size**: Gaussian on `|ln(comp hour-1) − ln(target hour-1)|`, bandwidth 1.5.
- **Pre-launch hype shape**: RMS distance between the two launches'
  centred daily log-mean viewer curves over the 14 days before release,
  bandwidth 1.5. A launch that hyped up the same way tends to play out
  the same way.
- **Platform**: console-only launches ×1.5 (GTA VI is PS5/Xbox Series only).
- **Research tier** (v2): the case file's unlock notes carry a `Tier:` tag.
  Early-access-contaminated launches ×0.25 (their pre-release peaks distort
  release-day curves) and weak-tier launches ×0.25 (F2P, live-service,
  slow-burn — poor analogues for a paid single-player AAA launch). Clean
  comparables ×1.0; absent/unknown tag → 1.0. 26 clean, 9 contaminated,
  2 weak in the pool.
- **Recency**: `exp(−(2026 − year)/10)`.
- **Unlock type**: rolling-midnight launches ×1.5 when the target is also
  rolling-midnight. Simultaneous-global launches jump at hour 1 already,
  so their flat ratio curves would drag the forecast down.

## Forecast

- Median: hour-1 print × exp(kernel-weighted mean log-ratio).
- Spread: kernel-weighted std of the log-ratios (floor 0.10) × 0.7;
  quantiles from normal z-scores (−1.645, −0.674, 0, 0.674, 1.645).
- **LOO bias correction**: leave-one-out over the comparables shows the
  ensemble under-forecasts rolling launches mid-day (hours 6–16) by
  +0.11…+0.18 log, so 0.5× that per-hour bias is added to the mean for
  rolling targets (derived in `dev/loo_bias.py` in the build workspace;
  the derivation uses only the case file's own comparables).

## What we deliberately do not do

- No persistence baseline: the house baseline (flat at hour 1) scores
  0.387 on practice; this ensemble scores 0.178.
- No ratios for the GTA VI category itself: its history in the case file
  is pre-release only (premiere onward), so it has no release day to
  learn ratios from.
- No weighted median: tested, much worse (0.37) — a single comparable's
  curve per hour is too noisy.
- No log-mean-exp centre: tested, worse (0.22) — it overshoots the median.
- No extra tuning beyond 5 constants (bandwidths, spread, unlock boost,
  bias shrinkage): 4 practice cases cannot support more without
  overfitting; the final is a single unseen launch.

## v2 changes (2026-11-17)

- Tier weighting (see above) + narrower kernels B1/BSHAPE 1.5 → 1.0.
  The (0.8–1.2, 0.8–1.2) bandwidth basin is smooth on the practice cases
  and (1.0, 1.0) is its centre; tier downweighting alone moves
  0.178 → 0.172, the narrower kernels take it to 0.164. Every practice
  case improves (p00 0.256→0.229, p01 0.152→0.134, p02 0.117→0.106,
  p03 0.188→0.187).
- Deliberately NOT used: per-hour spread from LOO residual SD (the LOO
  residual distribution, SD 0.7–1.1 log, is dominated by hard-to-predict
  small launches and does not transfer to big practice targets —
  empirical-quantile variants scored 0.209–0.225, far worse); per-hour
  CAL (coverage collapsed to 0.84–0.89); winsorised means; multi-bandwidth
  ensembles (no gain); a re-derived LOO bias curve under tier weights
  (worse on practice than the v1 curve — the bias is size-dependent, and
  the v1 curve from rolling comparables fits the big practice launches
  better). CAL stays 0.7 rather than the practice-optimal 0.6: the final
  target (GTA VI) extrapolates beyond every comparable in size, so its
  true uncertainty is larger than the practice cases suggest and a slightly
  wider spread hedges that.
- Practice validation (v2): mean pinball loss 0.164 vs house baseline
  0.387; 90% coverage 0.913; typical miss 27.7% (baseline 82.8%).
  Runtime ~0.5 s/case, deterministic (two runs byte-identical).

## Practice validation (v2)

Truth = SullyGnome "Average viewers" for the 4 practice games, release-day
hours 2..24 (anchored on the 8 consecutive history-tail values in each
`.in` file; hour-1 matches exactly). Mean pinball loss 0.164 vs house
baseline 0.387; 90% coverage 0.913; typical miss 27.7% (baseline 82.8%).
Runtime ~0.5 s/case, deterministic (two runs byte-identical). v1 scored
0.178 / 0.946 / 31.2% on the same truth.
