"""
data_loader.py — load spot, VIX, and option year files with light caching.
Option files are large (40-438 MB/yr); always pass columns= and load per-year.
"""
import os, gc
import numpy as np
import pandas as pd
from . import config as C

_spot_cache = None
_vix_cache  = None
_year_cache = {}

def load_spot():
    """dict: int64 ns -> spot close. Cached."""
    global _spot_cache
    if _spot_cache is None:
        s = pd.read_parquet(C.SPOT_PATH)
        t = pd.to_datetime(s["datetime"]).values.astype("datetime64[ns]").astype(np.int64)
        _spot_cache = dict(zip(t, s["close"].to_numpy(np.float64)))
    return _spot_cache

def load_spot_df():
    s = pd.read_parquet(C.SPOT_PATH)
    s["datetime"] = pd.to_datetime(s["datetime"])
    return s.sort_values("datetime").reset_index(drop=True)

def load_vix():
    """pd.Series indexed by normalized day -> vix (decimal). Cached."""
    global _vix_cache
    if _vix_cache is None:
        if not os.path.exists(C.VIX_PATH):
            _vix_cache = None
            return None
        v = pd.read_parquet(C.VIX_PATH)
        col = "close" if "close" in v.columns else v.columns[-1]
        vv = pd.DataFrame({"dt": pd.to_datetime(v["datetime"]), "vix": v[col].astype(float)})
        vv["day"] = vv["dt"].dt.normalize()
        daily = vv.groupby("day")["vix"].last().sort_index()
        if daily.median() > 1.5:      # quoted in %-points -> decimal
            daily = daily / 100.0
        _vix_cache = daily
    return _vix_cache

def load_year(year, columns=None):
    """Load one option year parquet as arrays dict. Cached per (year, columns key)."""
    key = (year, tuple(columns) if columns else None)
    if key in _year_cache:
        return _year_cache[key]
    f = os.path.join(C.OPT_DIR, f"year={year}.parquet")
    if not os.path.exists(f):
        _year_cache[key] = None
        return None
    cols = columns or ["expiry", "strike", "option_type", "datetime",
                       "open", "high", "low", "close", "volume", "open_interest", "expiry_type"]
    df = pd.read_parquet(f, columns=cols)
    df = df[df["expiry"].notna()].reset_index(drop=True)
    out = {"df": df}  # keep as DataFrame; snapshot code slices it
    _year_cache[key] = out
    return out

def clear_cache():
    global _year_cache
    _year_cache = {}
    gc.collect()
