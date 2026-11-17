[![make.fun](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/sanschiko3-dotcom/gta6-twitch-ccu-forecast-01/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/sanschiko3-dotcom/gta6-twitch-ccu-forecast-01/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01)

# GTA VI launch-day Twitch viewers, hour by hour

Entry for [Forecast GTA VI's launch-day Twitch viewers hour by hour](https://make.fun/bounty/gta6-twitch-ccu-forecast-01) (make.fun).

`main.py` (Python 3.13, standard library only, no network, deterministic)
reads one case file `/input/<id>.in` — hour 1's print plus the release-day
curves of comparable past launches — and writes `/output/<id>.out` with five
quantiles (5/25/50/75/95%) of Twitch concurrent viewers for each of hours
2..24 of release day.

## Model: practice-anchored comparable-kernel ensemble

For each comparable launch, take its release-day log-ratio curve
`r_h = ln(viewers_h / viewers_hour1)`. Weight each comparable with a kernel
on:

- **launch size** — distance between log hour-1 prints;
- **pre-launch hype shape** — RMS distance between centred daily log-mean
  curves over the 14 days before release;
- **platform** — console-only launches (no PC) get a 1.5x boost, since
  GTA VI is console-only (PS5 / Xbox Series X|S);
- **recency** — mild decay by release year;
- **unlock type** — rolling-midnight-local launches get a 1.5x boost when
  the target also unlocks by rolling midnight (all practice launches and
  GTA VI do; simultaneous-global launches ramp earlier and would flatten
  the forecast curve).

The forecast median is hour 1's print times the kernel-weighted mean ratio;
the spread is the kernel-weighted standard deviation of the ratios (floored,
times a calibration factor). A leave-one-out residual-bias correction,
estimated from the 12 rolling-midnight comparables, is added to the mean for
rolling targets (see `STRATEGY.md`). The GTA VI category's own pre-release
history has no release day, so it is excluded from the ratio ensemble —
no ratios are invented for it.

## What's new in v2

- **Tier weighting** — each comparable's unlock note carries a `Tier:` tag
  from the case file's own research. Early-access-contaminated launches
  (9 of 38: pre-release peaks distort their release-day curves) and
  weak-tier launches (2: F2P, live-service, slow-burn) are downweighted
  to 0.25x; clean comparables stay at 1.0x.
- **Narrower kernels** — bandwidths B1/BSHAPE 1.5 → 1.0. With the noisy
  comparables downweighted, the (0.8–1.2, 0.8–1.2) bandwidth basin is
  smooth and (1.0, 1.0) is its centre on the 4 practice cases.
- Everything else unchanged (CAL 0.7, unlock boost 1.5, LOO bias
  correction at 0.5x shrink).

## Practice results (dev, vs SullyGnome truth)

| case | game | loss v1 | loss v2 | 90% coverage v2 |
|------|------|---------|---------|-----------------|
| p00 | Marvel's Wolverine | 0.256 | 0.229 | 1.000 |
| p01 | Red Dead Redemption 2 | 0.152 | 0.134 | 0.957 |
| p02 | God of War Ragnarök | 0.117 | 0.106 | 0.957 |
| p03 | Marvel's Spider-Man 2 | 0.188 | 0.187 | 0.739 |
| **mean** | | **0.178** | **0.164** | **0.913** |

House baseline on the same truth: **0.387** loss, 0.783 coverage
(the baseline figures reproduce the house's published 0.387 / 82.8% /
0.783 exactly, which validates the truth data). Runtime ~0.5 s per case,
two runs byte-identical. Typical miss 27.7% (v1: 31.2%).

## Run it

```sh
mkdir -p out
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

## License

MIT — see [LICENSE](LICENSE).
