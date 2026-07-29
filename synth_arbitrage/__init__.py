"""SynthRadar Arbitrage & Scraper Package.

Exposes configuration constants, evaluation functions, multi-platform scrapers,
and database interface classes.
"""

from synth_arbitrage.analysis import analyze_listing, extract_price, get_market_price
from synth_arbitrage.config import (
    ACCESSORY_KEYWORDS,
    CONDITION_DEFEKT,
    CONDITION_IGNORE,
    CONDITION_MINT,
    CONDITION_POOR,
    DEFECTIVE_KEYWORDS,
    JUNK_KEYWORDS,
    MARKET_VALUES,
    TARGET_BRANDS,
    load_or_create_config,
    safe_json_read,
    safe_json_write,
)
from synth_arbitrage.database import SupabaseDB
from synth_arbitrage.scraper import (
    scrape_all_platforms,
    scrape_ebay_brand,
    scrape_kleinanzeigen_brand,
    scrape_thomann_bstock,
)

__all__ = [
    # Config constants & utils
    "JUNK_KEYWORDS",
    "ACCESSORY_KEYWORDS",
    "DEFECTIVE_KEYWORDS",
    "CONDITION_DEFEKT",
    "CONDITION_MINT",
    "CONDITION_POOR",
    "CONDITION_IGNORE",
    "TARGET_BRANDS",
    "MARKET_VALUES",
    "load_or_create_config",
    "safe_json_write",
    "safe_json_read",
    # Analysis functions
    "get_market_price",
    "extract_price",
    "analyze_listing",
    # Scraper routines
    "scrape_kleinanzeigen_brand",
    "scrape_ebay_brand",
    "scrape_thomann_bstock",
    "scrape_all_platforms",
    # Database client
    "SupabaseDB",
]
