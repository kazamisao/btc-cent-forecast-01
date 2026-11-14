#!/usr/bin/env python3
"""BTC 4-hour-ahead forecaster for make.fun btc-cent-forecast-01.

Approach (v2, fixed parameters): a damped mean-reversion forecaster in
log-price space.
  forecast = P_t * exp(drift)
  drift    = -0.15 * (log P_t - log P_{t-240})   (revert the last 4h move)
           - 0.30 * (log P_t - log P_{t-120})   (revert the last 2h move)
           + 0.10 * (mean log-price over 24h - log P_t)
The drift is capped at +/-2% so a single violent move can never drag the
forecast far.

Why this shape: on the six practice cases, adjacent non-overlapping
240-minute log-changes correlate about -0.3, i.e. a 4-hour move tends to
partially reverse over the next 4 hours, and the same holds at the 2-hour
scale. Short-horizon momentum, by contrast, made the walk-forward error
worse than persistence in every variant tried, so it is not used.

Why FIXED parameters instead of per-run adaptive selection: an adaptive
variant (walk-forward grid search inside each case, top-3 averaging, with
a persistence fallback) was built and tested first (v1). In a nested
walk-forward backtest it scored 47,030 cents against 44,212 for the fixed
parameters on the same 132 pseudo-checkpoints -- the per-case selection
noise outweighs any regime adaptation. The fixed parameters sit on a flat
optimum (the ten best grid neighbours span only 42,667-43,231 cents), so
the choice is not a sharp overfit peak.

Walk-forward backtest (pseudo-checkpoints every 60 min over the last 48h
of each practice case, 270 checkpoints; every 120 min, 132 checkpoints):
  step 60:  model 40,816.29 cents ($408.16) vs persistence 45,116.64 ($451.17)
  step 120: model 42,667.02 cents ($426.67) vs persistence 49,068.85 ($490.69)
  The model beats persistence on all six practice cases individually
  (improvements 4.5%-17.4% at step 120). The official practice baseline
  on the six real checkpoints is 44,521.58 cents; these backtest numbers
  are an estimate, not that score.

Standard library only, no network, deterministic (no randomness anywhere).
Reads $MAKEFUN_INPUT_DIR (default /input), writes $MAKEFUN_OUTPUT_DIR
(default /output), one <id>.out per <id>.in found.
"""

import json
import math
import os
import sys

HORIZON_DEFAULT = 240
DRIFT_CAP = 0.02            # never forecast a move larger than 2% in log terms

# Fixed reversion weights, chosen by walk-forward backtest on the practice
# cases (see module docstring). Flat optimum: neighbours within ~1%.
K_240 = 0.15                # weight on the last-horizon log change
K_120 = 0.30                # weight on the last-half-horizon log change
B_MEAN = 0.10               # weight on reversion to the 24h mean log-price
MEAN_WINDOW_MIN = 1440      # 24 hours


def _log_prices(prices):
    """Log prices, or None if any price is unusable."""
    out = []
    for p in prices:
        if not isinstance(p, (int, float)) or p <= 0.0 or not math.isfinite(p):
            return None
        out.append(math.log(p))
    return out


def forecast(prices, horizon=HORIZON_DEFAULT):
    """Forecast the price `horizon` minutes after the last price."""
    if not prices:
        return 0.0
    last = prices[-1]
    logp = _log_prices(prices)
    n = len(prices)
    half = horizon // 2
    if logp is None or n < MEAN_WINDOW_MIN + 1 or n <= horizon:
        return float(last)
    r_long = logp[n - 1] - logp[n - 1 - horizon]
    r_short = logp[n - 1] - logp[n - 1 - half]
    mean_log = sum(logp[n - MEAN_WINDOW_MIN:n]) / MEAN_WINDOW_MIN
    dev = mean_log - logp[n - 1]
    drift = -K_240 * r_long - K_120 * r_short + B_MEAN * dev
    if drift > DRIFT_CAP:
        drift = DRIFT_CAP
    elif drift < -DRIFT_CAP:
        drift = -DRIFT_CAP
    price = last * math.exp(drift)
    if not math.isfinite(price) or price <= 0.0:
        return float(last)
    return round(price, 2)


def main():
    input_dir = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
    output_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(output_dir, exist_ok=True)
    names = sorted(
        f for f in os.listdir(input_dir) if f.endswith(".in")
    )
    for name in names:
        case_id = name[:-3]
        with open(os.path.join(input_dir, name), "r", encoding="utf-8") as fh:
            case = json.load(fh)
        horizon = int(case.get("horizon_minutes", HORIZON_DEFAULT))
        prices = case["markets"][0]["prices"]
        price = forecast(prices, horizon)
        out = {"forecasts": [{"case": case["case"], "price": price}]}
        with open(
            os.path.join(output_dir, case_id + ".out"), "w", encoding="utf-8"
        ) as fh:
            json.dump(out, fh, separators=(",", ":"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
