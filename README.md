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

## Practice results (dev, vs SullyGnome truth)

| case | game | loss | 90% coverage |
|------|------|------|--------------|
| p00 | Marvel's Wolverine | 0.256 | 1.000 |
| p01 | Red Dead Redemption 2 | 0.152 | 0.957 |
| p02 | God of War Ragnarök | 0.117 | 1.000 |
| p03 | Marvel's Spider-Man 2 | 0.188 | 0.826 |
| **mean** | | **0.178** | **0.946** |

House baseline on the same truth: **0.387** loss, 0.783 coverage
(the baseline figures reproduce the house's published 0.387 / 82.8% /
0.783 exactly, which validates the truth data). Runtime ~0.5 s per case,
two runs byte-identical.

## Run it

```sh
mkdir -p out
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

## License

MIT — see [LICENSE](LICENSE).
