"""
pinning_study.py — STUDY 2: expiry-day pinning toward max-pain / high-OI strike.
Hypothesis: on weekly expiry days, spot is drawn toward the max-pain strike
(dealer gamma hedging). Tests whether |spot - maxpain| shrinks into the close
and whether spot closes near max-pain more than chance.

Run on server:  python -m studies.pinning_study 2023
"""
import sys, os
import numpy as np, pandas as pd
from core import config as C
from core import data_loader as DL
from core.chain import chain_at

def study_year(year):
    yd = DL.load_year(year, columns=["expiry","strike","option_type","datetime",
                                     "close","expiry_type","open_interest"])
    if yd is None: print(f"no data {year}"); return
    df = yd["df"]; smap = DL.load_spot()
    weekly_exps = sorted(df[df["expiry_type"]=="weekly"]["expiry"].unique())
    rows = []
    for E in weekly_exps:
        Eday = pd.Timestamp(E).normalize()
        # morning snapshot (09:20) and pre-close (15:20) on expiry day
        for tag, hhmm in [("0920",(9,20)),("1520",(15,20))]:
            ts = pd.Timestamp(Eday) + pd.Timedelta(hours=hhmm[0], minutes=hhmm[1])
            snap = chain_at(ts, expiry_types=("weekly",), iv=False, grk=False, year_df=yd)
            if snap is None: continue
            try: mp = snap.max_pain(E)
            except: mp = np.nan
            rows.append({"expiry":E,"tag":tag,"spot":snap.spot,"max_pain":mp,
                         "dist":abs(snap.spot-mp) if not np.isnan(mp) else np.nan})
    res = pd.DataFrame(rows)
    out = os.path.join(C.OUT_DIR, f"pinning_{year}.csv"); res.to_csv(out, index=False)
    # did distance to max-pain shrink from 09:20 to 15:20?
    piv = res.pivot_table(index="expiry", columns="tag", values="dist")
    if {"0920","1520"}.issubset(piv.columns):
        shrink = (piv["1520"] < piv["0920"]).mean()
        print(f"{year}: {len(piv)} expiries. dist to max-pain shrank into close in {shrink*100:.0f}% of them")
        print(f"  mean dist 09:20 = {piv['0920'].mean():.0f} pts -> 15:20 = {piv['1520'].mean():.0f} pts")
    print(f"  saved -> {out}")

if __name__ == "__main__":
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2023
    study_year(year)
