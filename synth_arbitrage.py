"""SynthRadar CLI entry point and backward compatibility top-level module.

Re-exports all configuration constants, evaluation functions, scrapers, and database
clients from the `synth_arbitrage` package for full backward compatibility.
"""

import asyncio
from datetime import datetime
import logging

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

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


async def main_async() -> None:
    """Asynchronous main loop orchestrating scraping and database persistence."""
    print("🤖 Iniciando Bot Experto en Arbitraje de Sintetizadores (Cloud Version)...")

    opportunities = await scrape_all_platforms()

    if opportunities:
        for opp in opportunities:
            opp["Fecha Agregado"] = datetime.now().strftime("%d/%m/%Y %H:%M")

        db = SupabaseDB()
        print(f"Upserting {len(opportunities)} opportunities to Supabase...")
        db.upsert_listings(opportunities)
        print(f"\n✅ Ciclo completado. {len(opportunities)} nuevas/actualizadas.")
    else:
        print("Ciclo vacío o abortado.")


def main() -> None:
    """CLI entry point for SynthRadar scraper execution."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
