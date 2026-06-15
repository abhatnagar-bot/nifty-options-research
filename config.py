"""
config.py — central paths & constants for the NIFTY options research repo.
Edit DATA_ROOT if your server layout differs.
"""
import os

# --- data locations (on the EC2 server) ---
DATA_ROOT = os.path.expanduser("~/option-trading/weekly_dataset")
OPT_DIR   = os.path.join(DATA_ROOT, "nifty_options_2019_2026")   # year=YYYY.parquet
SPOT_PATH = os.path.join(DATA_ROOT, "nifty_spot_2019_2026.parquet")
VIX_PATH  = os.path.join(DATA_ROOT, "india_vix.parquet")
OUT_DIR   = os.path.join(DATA_ROOT, "research_outputs")

# --- market / model constants ---
LOT          = 75
R            = 0.06      # risk-free
Q            = 0.0       # dividend yield
ANNUAL       = 52        # weekly periods/yr (for strategy metrics)
TRADING_DAYS = 252       # for vol annualization
MAX_ATM_GAP  = 60        # pts; ignore ATM if nearest strike farther than this

# --- time helpers (datetimes handled as int64 ns) ---
MIN_NS  = 60 * 1_000_000_000
DAY_NS  = 86_400_000_000_000
IST_OPEN_NS  = (9*3600 + 15*60) * 1_000_000_000   # 09:15
IST_920_NS   = (9*3600 + 20*60) * 1_000_000_000   # 09:20 typical entry
IST_CLOSE_NS = (15*3600 + 30*60) * 1_000_000_000  # 15:30

CE, PE = "CE", "PE"

os.makedirs(OUT_DIR, exist_ok=True)
