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

- **Size**: Gaussian on `|ln(comp hour-1) − ln(target hour-1)|`, bandwidth
  per hour band (v3): early hours 2–8 use 1.6, mid hours 9–16 use 0.7,
  late hours 17–24 use 1.2.
- **Pre-launch hype shape**: RMS distance between the two launches'
  centred daily log-mean viewer curves over the 14 days before release,
  bandwidth per hour band (v3): 1.6 early, 0.7 mid, 1.2 late. A launch
  that hyped up the same way tends to play out the same way.
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
- **LOO bias correction (v3)**: leave-one-out over the comparables shows
  the ensemble under-forecasts rolling launches mid-day (hours 6–16) by
  +0.07…+0.15 log, so a per-hour bias is added to the mean for rolling
  targets (re-derived in `dev/v3_tune.py` under v2 weights, from the
  rolling-midnight comparables only), scaled per hour band: 1.0× early,
  0.25× mid, 1.0× late. Mid hours are well determined by the kernel
  ensemble, so the LOO bias — dominated by hard small launches —
  over-corrects there.

## What we deliberately do not do

- No persistence baseline: the house baseline (flat at hour 1) scores
  0.387 on practice; this ensemble scores 0.150.
- No ratios for the GTA VI category itself: its history in the case file
  is pre-release only (premiere onward), so it has no release day to
  learn ratios from.
- No weighted median: tested, much worse (0.37) — a single comparable's
  curve per hour is too noisy.
- No log-mean-exp centre: tested, worse (0.22) — it overshoots the median.
- No extra tuning beyond the band table and bias bands: 4 practice cases
  cannot support more without overfitting; the final is a single unseen
  launch. Every added knob was required to win independently and to sit in
  a smooth neighbourhood (see v3 notes below).

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

## v3 changes (2026-11-17)

- Per-hour-band kernels: (B1, BSHAPE) = (1.6, 1.6) early (h2–8),
  (0.7, 0.7) mid (h9–16), (1.2, 1.2) late (h17–24), CAL 0.7 throughout.
  Early/late ratio curves are noisier, so wider kernels average more
  comparables; mid hours are the most stable, so tighter kernels
  discriminate. Bands alone move v2 0.164 → 0.156; the band basin is
  smooth — neighbours (early 1.4, mid 0.7/0.8, late 1.0/1.4) score
  0.151–0.155.
- Re-derived LOO bias curve (under v2 weights) + per-band shrink
  (1.0, 0.25, 1.0). The curve alone at uniform 0.5× scores 0.1645 —
  the win is the band pattern, not the curve: mid hours need little
  correction. Bias alone moves 0.164 → 0.159; combined with the bands
  the model reaches 0.150.
- Deliberately NOT used: console factor 1.0/1.25 (the gain is entirely
  p00-driven while p01/p02/p03 all regress, and GTA VI is console-only
  at launch, so the console prior stays at 1.5); Pearson-correlation
  shape distance, effective-sample spread inflation, persistence
  shrinkage, 7/10-day shape windows, two-kernel mixture (all measured
  no gain or worse). Full experiment record: dev/v3_results.md in the
  build workspace.
- Practice validation (v3): mean pinball loss **0.150441** vs v2 0.164038
  and house baseline 0.387097; 90% coverage 0.946; typical miss 25.3%
  (per case: p00 0.208, p01 0.136, p02 0.089, p03 0.169 — 3 of 4 improve
  substantially, only p01 regresses by 0.002). Runtime ~0.5 s/case,
  deterministic (two runs byte-identical).
