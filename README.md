# NIFTY Options Inefficiency Research

Infrastructure + studies for mining NIFTY weekly/monthly options (2019–2026,
minute data, full chain with OI) for **structural inefficiencies** — not just the
volatility risk premium. Built on a clean "chain snapshot" core so every analysis
is a query on the full IV surface + greeks + OI at any timestamp.

## Data (on EC2 server, NOT in repo — see .gitignore)
- `~/option-trading/weekly_dataset/nifty_options_2019_2026/year=YYYY.parquet`
  cols: instrument, expiry, strike, option_type(CE/PE), datetime(IST minute),
  open, high, low, close, volume, open_interest, expiry_type(weekly/monthly), source
- `~/option-trading/weekly_dataset/nifty_spot_2019_2026.parquet` — spot minute OHLC
- `~/option-trading/weekly_dataset/india_vix.parquet` — India VIX EOD (%-points)

## Layout
```
core/
  config.py        paths + constants (LOT=75, r=0.06, q=0, ANNUAL=52, ns helpers)
  blackscholes.py  European BS price, bisection IV inversion, greeks (delta/gamma/vega/theta)
  data_loader.py   cached loaders: spot dict, VIX series, per-year option DataFrame
  chain.py         **CORE**: chain_at(ts) -> ChainSnapshot
                     .surface (expiry,strike,type,price,iv,greeks,oi,vol,T,moneyness)
                     .term_structure() / .atm_iv(e) / .skew(e) / .skew_slope(e)
                     .oi_by_strike(e) / .max_pain(e)
  _selftest.py     verifies BS round-trip, greek signs, put-call parity
studies/
  parity_scan.py   STUDY 1: put-call parity violation scanner (model-free)
  pinning_study.py STUDY 2: expiry-day pinning to max-pain (dealer gamma)
outputs/           CSVs written by studies (gitignored)
notebooks/         Colab plotting (load output CSVs, chart)
```

## Setup (on server)
```bash
pip install -r requirements.txt --break-system-packages
python -m core._selftest          # should print PASSED
```

## Run a study
```bash
python -m studies.parity_scan 2023
python -m studies.pinning_study 2023
```
Outputs land in `~/option-trading/weekly_dataset/research_outputs/`; scp them to
laptop and plot in Colab.

## The chain snapshot (how everything works)
```python
import pandas as pd
from core.chain import chain_at
snap = chain_at(pd.Timestamp('2023-03-15 12:00'))
snap.spot                 # spot at that minute
snap.surface              # full tidy chain: IV, greeks, OI for every strike/expiry
snap.term_structure()     # ATM IV per expiry (the vol curve)
snap.skew(expiry)         # IV vs moneyness (the smile)
snap.skew_slope(expiry)   # put-side minus call-side IV (skew steepness)
snap.max_pain(expiry)     # max-pain strike from OI
```

## Research roadmap (inefficiencies to mine, ~ by findability)
1. **Static no-arbitrage** (model-free): put-call parity, vertical/butterfly/
   calendar bounds. Start here — validates data + may find clean violations. [parity_scan.py]
2. **IV surface dynamics**: skew over/under-reaction, term-structure RV, PCA of
   surface moves (level/slope/curvature), calendar mispricings.
3. **Intraday microstructure** (minute data is rare — exploit): time-of-day IV
   patterns, optimal entry timing, expiry-day gamma/pinning. [pinning_study.py]
4. **OI / positioning**: dealer gamma proxy from OI-by-strike → predicts intraday
   vol-of-spot (short gamma = amplify, long = dampen); OI buildup as magnet/repel.
5. **Cross-sectional RV**: locally-rich strikes vs fitted smile (relative value).

## Discipline (lessons carried from prior work)
- State the **mechanism** before testing ("mispriced *because* dealers must hedge X").
- Validate **out-of-sample AND across regimes** — an edge that dies in turbulence
  (e.g. 2023) is not robust. Prior per-trade ML filter looked great on 2024–25
  (AUC 0.63) but inverted on 2023 (AUC 0.42) — classic favorable-window overfit.
- Everything **gross of costs**; recheck after costs since inefficiencies are small.
- Prior validated edge: slope<0 entry filter (term-structure), flat-sized — regime
  level, not per-trade predictable.
