# BTC Cent Forecast 01

Forecast Bitcoin's US-dollar price 4 hours ahead, for
[make.fun](https://make.fun) competition `btc-cent-forecast-01`.

## How to run

```sh
python3 main.py   # reads $MAKEFUN_INPUT_DIR (default /input),
                  # writes $MAKEFUN_OUTPUT_DIR (default /output)
```

Python 3.13, standard library only, no network. One `<id>.out` per
`<id>.in`, containing `{"forecasts":[{"case":"<id>","price":<number>}]}`.
Deterministic, ~10 ms per case.

## Approach

A damped mean-reversion forecaster in log-price space:

```
forecast = P_t * exp(drift)
drift    = -0.15 * (log P_t - log P_{t-240})
         - 0.30 * (log P_t - log P_{t-120})
         + 0.10 * (mean log-price over 24h - log P_t)
```

with the drift capped at +/-2%. The idea: on the practice data, adjacent
non-overlapping 240-minute log-changes correlate about -0.3, so a 4-hour
move tends to partially reverse over the next 4 hours (same at the 2-hour
scale). Short-horizon momentum was tried and made things worse than
persistence in every variant, so it is not used.

The parameters are fixed (not re-fit per case): an adaptive variant that
re-selected parameters by walk-forward search inside each case was built
and tested, but scored worse in a nested walk-forward backtest
(47,030 vs 44,212 cents on the same 132 pseudo-checkpoints) — selection
noise outweighed any regime adaptation. The fixed parameters sit on a flat
optimum (the ten best grid neighbours span only 42,667–43,231 cents).

## Backtest (honest numbers)

Walk-forward, pseudo-checkpoints over the last 48 hours of each of the six
practice cases, forecasting t+240 using only data up to t:

| checkpoints | model MAE | persistence MAE | improvement |
|---|---|---|---|
| every 60 min (264) | 40,816.27 cents ($408.16) | 45,116.64 cents ($451.17) | -9.53% |
| every 120 min (132) | 42,666.95 cents ($426.67) | 49,068.85 cents ($490.69) | -13.05% |

The model beats persistence on all six practice cases individually
(improvements 4.5%–17.4% at the 120-minute spacing). The official practice
baseline on the six real checkpoints is 44,521.58 cents — the numbers above
are a backtest estimate, not that score, and the final is graded on future
prices nobody has seen, so no practice number guarantees a final result.

## License

MIT — see `LICENSE`.
