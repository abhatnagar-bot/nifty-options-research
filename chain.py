"""
chain.py — THE core object. At any timestamp, build the full option chain:
strikes x expiries x {CE,PE} with price, inverted IV, greeks, OI, volume.
Everything else (skew, term structure, pinning, parity, dealer gamma) is a
query on a ChainSnapshot.

Usage:
    from core.chain import chain_at
    snap = chain_at(pd.Timestamp('2023-03-15 09:20'))
    snap.surface   # tidy DataFrame: expiry,strike,type,price,iv,delta,gamma,vega,oi,vol,T,moneyness
    snap.atm_iv(expiry)        # ATM IV for one expiry
    snap.term_structure()      # ATM IV per expiry (the curve)
    snap.skew(expiry)          # IV vs moneyness for one expiry
"""
import numpy as np
import pandas as pd
from . import config as C
from . import data_loader as DL
from .blackscholes import implied_vol, greeks

def _ns(ts):
    return pd.Timestamp(ts).value

class ChainSnapshot:
    def __init__(self, ts, spot, surface):
        self.ts = pd.Timestamp(ts)
        self.spot = spot
        self.surface = surface   # tidy DataFrame

    # ---- term structure ----
    def expiries(self):
        return sorted(self.surface["expiry"].unique())

    def atm_iv(self, expiry):
        s = self.surface[self.surface["expiry"] == expiry]
        if s.empty: return np.nan
        atm = s.iloc[(s["strike"] - self.spot).abs().argmin()]["strike"]
        leg = s[s["strike"] == atm]
        return leg["iv"].mean()  # avg of CE & PE ATM IV

    def term_structure(self):
        rows = []
        for e in self.expiries():
            s = self.surface[self.surface["expiry"] == e]
            T = s["T"].iloc[0]
            rows.append({"expiry": e, "T": T, "atm_iv": self.atm_iv(e),
                         "dte_cal": (pd.Timestamp(e).normalize() - self.ts.normalize()).days})
        return pd.DataFrame(rows).sort_values("T").reset_index(drop=True)

    # ---- skew / smile ----
    def skew(self, expiry, option_type=None):
        s = self.surface[self.surface["expiry"] == expiry].copy()
        if option_type: s = s[s["type"] == option_type]
        s = s.dropna(subset=["iv"]).sort_values("moneyness")
        return s[["strike", "moneyness", "type", "iv", "delta", "oi", "volume"]]

    def skew_slope(self, expiry, lo_mny=-0.05, hi_mny=0.05):
        """25d-ish skew proxy: IV(put side) - IV(call side) across a moneyness band."""
        s = self.surface[(self.surface["expiry"] == expiry)].dropna(subset=["iv"])
        below = s[(s["moneyness"] < 0) & (s["moneyness"] > lo_mny)]
        above = s[(s["moneyness"] > 0) & (s["moneyness"] < hi_mny)]
        if below.empty or above.empty: return np.nan
        return below["iv"].mean() - above["iv"].mean()

    # ---- positioning ----
    def oi_by_strike(self, expiry):
        s = self.surface[self.surface["expiry"] == expiry]
        return s.groupby(["strike", "type"])["oi"].first().unstack(fill_value=0)

    def max_pain(self, expiry):
        """Strike minimizing total option-holder payout (classic max-pain)."""
        s = self.surface[self.surface["expiry"] == expiry]
        oi = s.groupby(["strike", "type"])["oi"].first().unstack(fill_value=0)
        strikes = oi.index.values
        ce = oi.get("CE", pd.Series(0, index=oi.index)).values
        pe = oi.get("PE", pd.Series(0, index=oi.index)).values
        pains = []
        for Kp in strikes:
            call_pay = np.maximum(Kp - strikes, 0) * ce   # writer loss if expire at Kp
            put_pay  = np.maximum(strikes - Kp, 0) * pe
            pains.append(call_pay.sum() + put_pay.sum())
        return float(strikes[int(np.argmin(pains))])


def chain_at(ts, expiry_types=("weekly", "monthly"), iv=True, grk=True,
             strike_band=None, year_df=None):
    """
    Build a ChainSnapshot at timestamp ts (minute precision).
    strike_band: optional (low,high) absolute strikes to limit work; default all.
    """
    ts = pd.Timestamp(ts); nsv = ts.value
    y = ts.year
    yd = year_df if year_df is not None else DL.load_year(y)
    if yd is None: return None
    df = yd["df"]
    # slice this exact minute
    dns = pd.to_datetime(df["datetime"]).values.astype("datetime64[ns]").astype(np.int64)
    at = dns == nsv
    if not at.any(): return None
    snap = df[at].copy()
    if expiry_types:
        snap = snap[snap["expiry_type"].isin(expiry_types)]
    spot = DL.load_spot().get(nsv, np.nan)
    if np.isnan(spot) or snap.empty: return None
    if strike_band:
        lo, hi = strike_band
        snap = snap[(snap["strike"] >= lo) & (snap["strike"] <= hi)]

    rows = []
    exp_ns_map = {e: (pd.Timestamp(e).normalize().value) for e in snap["expiry"].unique()}
    for _, r in snap.iterrows():
        K = float(r["strike"]); typ = r["option_type"]; price = float(r["close"])
        is_call = (typ == "CE")
        T = max((exp_ns_map[r["expiry"]] - (nsv)) / C.DAY_NS, 1) / 365.0
        v = implied_vol(price, spot, K, T, C.R, C.Q, is_call) if iv else np.nan
        g = greeks(spot, K, T, v, C.R, C.Q, is_call) if (grk and not np.isnan(v)) else \
            dict(delta=np.nan, gamma=np.nan, vega=np.nan, theta=np.nan)
        rows.append({"expiry": r["expiry"], "strike": K, "type": typ, "price": price,
                     "iv": v, "delta": g["delta"], "gamma": g["gamma"], "vega": g["vega"],
                     "theta": g["theta"], "oi": float(r.get("open_interest", np.nan)),
                     "volume": float(r.get("volume", np.nan)), "T": T,
                     "moneyness": np.log(K / spot)})
    surface = pd.DataFrame(rows)
    return ChainSnapshot(ts, spot, surface)
