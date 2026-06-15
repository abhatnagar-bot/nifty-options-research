"""
parity_scan.py — STUDY 1: put-call parity violation scanner.
Model-free inefficiency check. For sampled timestamps, for each (expiry,strike)
with both CE & PE quotes, compute parity gap:
    gap = (C - P) - (S*e^-qT - K*e^-rT)
Large persistent gaps beyond cost = arbitrage or (usually) stale quotes.
Characterizes WHEN/ WHERE parity breaks (dte, moneyness, time-of-day).

Run on server:  python -m studies.parity_scan 2023
"""
import sys, os
import numpy as np, pandas as pd
from math import exp
from core import config as C
from core import data_loader as DL

def scan_year(year, sample_minutes=40):
    yd = DL.load_year(year, columns=["expiry","strike","option_type","datetime",
                                     "close","expiry_type","open_interest"])
    if yd is None:
        print(f"no data for {year}"); return
    df = yd["df"]; smap = DL.load_spot()
    df["ns"] = pd.to_datetime(df["datetime"]).values.astype("datetime64[ns]").astype(np.int64)
    # sample a set of minutes (e.g. one per trading day at ~12:00) to keep it light
    df["day"] = (df["ns"] // C.DAY_NS)
    noon = (12*3600)*1_000_000_000
    df["mindist"] = (df["ns"] % C.DAY_NS - noon).abs()
    picks = df.groupby("day")["ns"].apply(lambda s: s.iloc[(s % C.DAY_NS - noon).abs().argmin()])
    keep = set(picks.values)
    sub = df[df["ns"].isin(keep)]
    rows = []
    for nsv, g in sub.groupby("ns"):
        S = smap.get(int(nsv))
        if S is None: continue
        ce = g[g["option_type"]=="CE"].set_index(["expiry","strike"])["close"]
        pe = g[g["option_type"]=="PE"].set_index(["expiry","strike"])["close"]
        common = ce.index.intersection(pe.index)
        for (E,K) in common:
            T = max((pd.Timestamp(E).normalize().value - nsv)/C.DAY_NS,1)/365.0
            rhs = S*exp(-C.Q*T) - K*exp(-C.R*T)
            gap = (ce[(E,K)] - pe[(E,K)]) - rhs
            rows.append({"ns":nsv,"expiry":E,"strike":K,"S":S,"T":T,
                         "moneyness":np.log(K/S),"gap":gap,"gap_pct":gap/S*100})
    res = pd.DataFrame(rows)
    out = os.path.join(C.OUT_DIR, f"parity_{year}.csv"); res.to_csv(out, index=False)
    print(f"{year}: {len(res)} parity points across {sub['ns'].nunique()} minutes")
    if len(res):
        print(f"  median |gap| = {res.gap.abs().median():.2f} pts  ({res.gap_pct.abs().median():.4f}% of spot)")
        print(f"  95th pct |gap| = {res.gap.abs().quantile(.95):.2f} pts")
        print(f"  worst by DTE: short-dated tend to be noisier")
    print(f"  saved -> {out}")

if __name__ == "__main__":
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2023
    scan_year(year)
