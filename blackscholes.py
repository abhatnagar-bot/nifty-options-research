"""
blackscholes.py — European BS pricing, IV inversion (bisection), and greeks.
NIFTY index options are European, so plain BS with r,q is correct.
Vectorized where it matters; scalar fallbacks for clarity.
"""
import numpy as np
from math import log, sqrt, exp, erf

def _nc(x):  # standard normal CDF via erf
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))

def _npdf(x):
    return exp(-0.5 * x * x) / sqrt(2.0 * np.pi)

def bs_price(S, K, T, vol, r, q, is_call):
    if T <= 0 or vol <= 0:
        return max(S - K, 0.0) if is_call else max(K - S, 0.0)
    d1 = (log(S / K) + (r - q + 0.5 * vol * vol) * T) / (vol * sqrt(T))
    d2 = d1 - vol * sqrt(T)
    if is_call:
        return S * exp(-q * T) * _nc(d1) - K * exp(-r * T) * _nc(d2)
    return K * exp(-r * T) * _nc(-d2) - S * exp(-q * T) * _nc(-d1)

def implied_vol(price, S, K, T, r, q, is_call, lo=1e-3, hi=5.0, iters=60):
    """Bisection IV. Returns np.nan if price below intrinsic or non-invertible."""
    if T <= 0 or price <= 0:
        return np.nan
    intr = max(S - K, 0.0) if is_call else max(K - S, 0.0)
    if price <= intr + 1e-6:
        return np.nan
    a, b = lo, hi
    for _ in range(iters):
        m = 0.5 * (a + b)
        if bs_price(S, K, T, m, r, q, is_call) > price:
            b = m
        else:
            a = m
    return 0.5 * (a + b)

def greeks(S, K, T, vol, r, q, is_call):
    """Return dict: delta, gamma, vega, theta(per yr), and d1/d2."""
    if T <= 0 or vol <= 0:
        return dict(delta=np.nan, gamma=np.nan, vega=np.nan, theta=np.nan, d1=np.nan, d2=np.nan)
    d1 = (log(S / K) + (r - q + 0.5 * vol * vol) * T) / (vol * sqrt(T))
    d2 = d1 - vol * sqrt(T)
    pdf = _npdf(d1)
    disc_q = exp(-q * T)
    delta = disc_q * _nc(d1) if is_call else disc_q * (_nc(d1) - 1.0)
    gamma = disc_q * pdf / (S * vol * sqrt(T))
    vega  = S * disc_q * pdf * sqrt(T)            # per 1.00 (100%) vol; /100 for per vol-point
    # theta (per year)
    term1 = -(S * disc_q * pdf * vol) / (2 * sqrt(T))
    if is_call:
        theta = term1 - r * K * exp(-r * T) * _nc(d2) + q * S * disc_q * _nc(d1)
    else:
        theta = term1 + r * K * exp(-r * T) * _nc(-d2) - q * S * disc_q * _nc(-d1)
    return dict(delta=delta, gamma=gamma, vega=vega, theta=theta, d1=d1, d2=d2)
