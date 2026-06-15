"""Run: python -m core._selftest  — verifies BS round-trips and greek signs."""
from .blackscholes import bs_price, implied_vol, greeks
S,K,T,vol,r,q = 25000,25000,30/365,0.15,0.06,0.0
c = bs_price(S,K,T,vol,r,q,True); p = bs_price(S,K,T,vol,r,q,False)
assert abs(implied_vol(c,S,K,T,r,q,True)-vol) < 1e-3, "call IV round-trip failed"
assert abs(implied_vol(p,S,K,T,r,q,False)-vol) < 1e-3, "put IV round-trip failed"
gc = greeks(S,K,T,vol,r,q,True); gp = greeks(S,K,T,vol,r,q,False)
assert 0 < gc["delta"] < 1, "call delta range"
assert -1 < gp["delta"] < 0, "put delta range"
assert gc["gamma"] > 0 and gc["vega"] > 0, "gamma/vega positive"
# put-call parity: C - P = S e^-qT - K e^-rT
from math import exp
lhs = c - p; rhs = S*exp(-q*T) - K*exp(-r*T)
assert abs(lhs-rhs) < 1e-4, f"parity {lhs:.4f} vs {rhs:.4f}"
print("core self-test PASSED: BS round-trip, greek signs, put-call parity all OK")
