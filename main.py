"""gta6-twitch-ccu-forecast-01: practice-anchored comparable-kernel ensemble.

Forecasts Twitch concurrent viewers in the Grand Theft Auto VI category for
hours 2..24 of release day, from hour 1's print plus the release-day curves
of comparable past launches shipped in the case file.

Model (per hour h, all in log space):
  - For each comparable, r_h = ln(viewers_h / viewers_hour1) on its release day.
  - Kernel weight per comparable:
        w = exp(-0.5*(d1/B1)^2) * exp(-0.5*(dshape/BSHAPE)^2)
            * platform_factor * recency_factor * unlock_factor * tier_weight
    d1     = |ln(comp hour-1) - ln(target hour-1)|   (similar launch size)
    dshape = RMS distance between the target's and the comparable's centred
             pre-launch daily log-mean curves (similar pre-launch hype shape)
    platform_factor = 1.5 for console-only launches (no PC), else 1.0
    recency_factor  = exp(-(2026 - release_year) / 10)
    unlock_factor   = 1.5 when both target and comparable unlock by rolling
                      midnight local (all practice launches and GTA VI do);
                      1.0 otherwise. Rolling launches ramp at 04:00-05:00Z
                      (US midnight) and peak late; simultaneous-global
                      launches jump earlier and would flatten the curve.
  - Median = p1 * exp(weighted mean of r_h); spread = weighted std of r_h
    (floored at 0.10), times CAL; quantiles via normal z.
  - The 'Grand Theft Auto VI category before release' comparable has no
    release day (its day_start is the 2026-08-27 premiere), so it is excluded
    from the ratio ensemble; no ratios are invented for it.

Tier weighting uses unlock-note tags: comparable = 1.0,
early-access-contaminated = 0.25, weak = 0.25; absent or unknown tags
receive 1.0. Early-access pre-release peaks distort release-day curves;
weak launches (F2P, live-service, slow-burn) are poor analogues for a paid
single-player AAA launch.

Kernel bandwidths are B1=1.0 and BSHAPE=1.0; G=0.0, CAL=0.7,
UNLOCK_BOOST=1.5. A leave-one-out residual-bias correction (ROLL_BIAS,
derived in dev/loo_bias.py from the 12 rolling-midnight comparables,
shrunk 0.5x) is added to the forecast mean for rolling targets.
Coordinator-verified expected dev result on the 4 practice cases:
practice mean pinball loss 0.164 (baseline 0.387), 90% coverage 0.913,
typical miss 27.7%. These numbers were not measured in this implementation.

Python 3.13, standard library only, no network, deterministic: comparables
are processed in name order, no randomness, no wall-clock use.
"""

import json
import math
import os
import re
import statistics
import sys
from datetime import datetime
from pathlib import Path

# The grader's -P leaves /bot off sys.path: put it back first, so a module
# shipped beside this file would import. (This entry is a single file.)
sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = (-1.645, -0.674, 0.0, 0.674, 1.645)

# Tuned constants (see module docstring).
B1 = 1.0
BSHAPE = 1.0
TIER_WEIGHTS = {"comparable": 1.0, "early-access-contaminated": 0.25, "weak": 0.25}
TIER_RE = re.compile(r"Tier:\s*([a-z\-]+)")
G = 0.0
CAL = 0.7
UNLOCK_BOOST = 1.5
CONSOLE_ONLY_FACTOR = 1.5
MIN_SD = 0.10
# Leave-one-out residual bias (mean true-minus-forecast log-ratio per hour
# over the 12 rolling-midnight comparables; see dev/loo_bias.py). Added to
# the forecast mean for rolling targets only, shrunk 0.5x.
BIAS_SHRINK = 0.5
ROLL_BIAS = {2: -0.05, 3: -0.06, 4: -0.04, 5: 0.00, 6: 0.13, 7: 0.18,
             8: 0.16, 9: 0.13, 10: 0.13, 11: 0.13, 12: 0.12, 13: 0.13,
             14: 0.13, 15: 0.11, 16: 0.09, 17: 0.08, 18: 0.07, 19: 0.03,
             20: 0.00, 21: -0.01, 22: -0.01, 23: 0.00, 24: 0.00}


def stamp(s):
    """ISO-8601 timestamp (with trailing Z) -> epoch seconds."""
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def hourly(points):
    """Points ({from|at, viewers}) -> {hour_epoch: mean viewers in that hour}."""
    bins = {}
    for p in points or []:
        v = p.get("viewers")
        if isinstance(v, (int, float)) and math.isfinite(v) and v > 0:
            t = int(stamp(p.get("from", p.get("at"))) // 3600)
            bins.setdefault(t, []).append(v)
    return {t: sum(v) / len(v) for t, v in sorted(bins.items())}


def daily(points, start):
    """Hourly {t: viewers} -> centred daily log-means for the 14 days before start.

    Returns {day_offset: centred log-mean} with day_offset in [-14, 0).
    Centring (subtracting the series' own 14-day mean) makes the shape
    comparable across launches of very different sizes.
    """
    bins = {}
    for t, v in sorted(points.items()):
        d = (t - start) // 24
        if -14 <= d < 0:
            bins.setdefault(d, []).append(math.log(v))
    means = {d: sum(v) / len(v) for d, v in sorted(bins.items())}
    centre = statistics.mean(means.values()) if means else 0.0
    return {d: v - centre for d, v in means.items()}


def is_rolling(text):
    """True when an unlock note describes a rolling midnight-local launch."""
    t = (text or "").lower()
    return ("rolling" in t) or ("midnight local" in t)


def round2(x):
    """x rounded to 2 decimals, half up (as the starter rounds it)."""
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if value.is_integer() else value


def prepare(case):
    """Extract the target's hour-1 print, pre-launch shape, and comparables.

    Returns (p1, comps, target_rolling) where each comp is
    (d1, dshape, factor, ratios, rolling, tier):
      d1     log distance between the comparable's and the target's hour-1
      dshape pre-launch shape distance (median of the others if <5 common days)
      factor platform x recency multiplier
      ratios {h: ln(viewers_h / viewers_1)} for h = 2..24
      rolling whether the comparable unlocked by rolling midnight local
      tier   unlock-note Tier tag, defaulting to comparable
    """
    known = sorted(case.get("known", []), key=lambda k: k["hour"])
    p1 = max(1, known[0]["viewers"]) if known else 1
    start = int(stamp(case["day_start"]) // 3600)
    target = daily(hourly(case.get("history_hourly") or case.get("history")), start)
    target_rolling = is_rolling(case.get("notes", ""))

    comps = []
    for c in sorted(case.get("comparables", []), key=lambda x: x["name"]):
        # GTA VI's premiere is not a release day: never invent launch ratios.
        if "Grand Theft Auto VI" in c["name"]:
            continue
        cstart = int(stamp(c["day_start"]) // 3600)
        pts = hourly(c.get("hourly"))
        v1 = pts.get(cstart, 0)
        ratios = {h: math.log(pts[cstart + h - 1] / v1) for h in range(2, 25)
                  if v1 > 0 and cstart + h - 1 in pts}
        if v1 <= 0 or len(ratios) < 12:
            continue
        shape = daily(pts, cstart)
        common = sorted(target.keys() & shape.keys())
        dist = (math.sqrt(sum((target[d] - shape[d]) ** 2 for d in common) / len(common))
                if len(common) >= 5 else None)
        factor = ((CONSOLE_ONLY_FACTOR if "PC" not in c.get("platforms", "").upper() else 1.0)
                  * math.exp(-(2026 - int(c["day_start"][:4])) / 10))
        tier_match = TIER_RE.search(c.get("unlock") or "")
        tier = tier_match.group(1) if tier_match else "comparable"
        comps.append((abs(math.log(v1) - math.log(p1)), dist, factor, ratios,
                      is_rolling(c.get("unlock", "")), tier))
    fallback = statistics.median([c[1] for c in comps if c[1] is not None] or [BSHAPE])
    comps = [(a, fallback if b is None else b, f, r, roll, tier)
             for a, b, f, r, roll, tier in comps]
    return p1, comps, target_rolling


def predict(prepared):
    """Kernel-weighted ensemble forecast: {"hours": [{"hour": h, "q": [...]}]}.

    Per hour, each comparable contributes its log-ratio with log-weight
    -0.5*(d1/B1)^2 - 0.5*(dshape/BSHAPE)^2 + ln(factor * unlock_boost
    * tier_weight); the median is the weighted mean of the ratios, the
    spread the weighted std (floored, x CAL), quantiles via normal z.
    """
    p1, comps, target_rolling = prepared
    rows = []
    for h in range(2, 25):
        present = []
        for d1, dshape, factor, ratios, rolling, tier in comps:
            if h not in ratios:
                continue
            boost = UNLOCK_BOOST if (target_rolling and rolling) else 1.0
            logw = (-0.5 * (d1 / B1) ** 2 - 0.5 * (dshape / BSHAPE) ** 2
                    + math.log(factor * boost) + math.log(TIER_WEIGHTS.get(tier, 1.0)))
            present.append((ratios[h], logw))
        if present:
            peak = max(w for _, w in present)
            vals = [(math.exp(w - peak), r) for r, w in present]
            total = sum(w for w, _ in vals)
            mean = sum(w * r for w, r in vals) / total
            sd = math.sqrt(sum(w * (r - mean) ** 2 for w, r in vals) / total)
        else:  # No comparable covers this hour: fall back to persistence.
            mean, sd = 0.0, 1.0
        if target_rolling:
            mean += BIAS_SHRINK * ROLL_BIAS.get(h, 0.0)
        spread = math.sqrt(max(sd, MIN_SD) ** 2 + (G * math.sqrt(h - 1)) ** 2) * CAL
        q = []
        for z in Z:
            value = p1 * math.exp(mean + z * spread)
            value = max(0.01, min(1e9, value))
            q.append(round2(value))
        # Rounding can only equalise neighbours, never invert them; enforce it.
        for i in range(1, 5):
            q[i] = max(q[i], q[i - 1])
        rows.append({"hour": h, "q": q})
    return {"hours": rows}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Every case file, in name order, so two runs write the same bytes.
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = predict(prepare(case))
        (OUTPUT_DIR / f"{path.stem}.out").write_text(
            json.dumps(forecast, separators=(",", ":")) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
