"""Cleanup script to remove stale and truncated listings from Supabase.

Removes:
- Listings with generic/truncated model names that don't match any MARKET_VALUES key
- Listings older than 7 days based on last_seen timestamp
"""

import os
import sys
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Known truncated/generic model names that should not exist in the DB
INVALID_MODELS = [
    "Korg Volca",       # Should be "Korg Volca Keys", "Korg Volca FM", etc.
    "Oberheim Matrix",  # Should be "Oberheim Matrix 1000", "Matrix 6", etc.
    "Roland Boutique",  # Too generic
]

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://wnoiyxgdbemamajebqom.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_VCnH38uDOJvfet7bJHRnAw_9VZaDSmp")


def cleanup():
    try:
        from supabase import create_client
    except ImportError:
        logging.error("supabase module not installed. Run: pip install supabase")
        # Fallback: use REST API with requests
        import requests

        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        base_url = f"{SUPABASE_URL}/rest/v1/listings"

        # 1. Delete truncated model names
        for model in INVALID_MODELS:
            url = f"{base_url}?modelo=eq.{model.replace(' ', '%20')}"
            resp = requests.delete(url, headers=headers)
            logging.info(f"DELETE modelo='{model}': status={resp.status_code}, deleted={len(resp.json()) if resp.ok else 0}")

        # 2. Delete stale listings (last_seen > 7 days ago)
        seven_days_ago = time.time() - (7 * 24 * 60 * 60)
        url = f"{base_url}?last_seen=lt.{seven_days_ago}"
        resp = requests.delete(url, headers=headers)
        logging.info(f"DELETE stale (last_seen < 7 days ago): status={resp.status_code}, deleted={len(resp.json()) if resp.ok else 0}")

        return

    # Use supabase client if available
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # 1. Delete truncated model names
    for model in INVALID_MODELS:
        try:
            resp = client.table("listings").delete().eq("modelo", model).execute()
            logging.info(f"Deleted {len(resp.data)} listings with modelo='{model}'")
        except Exception as e:
            logging.error(f"Error deleting modelo='{model}': {e}")

    # 2. Delete stale listings (last_seen > 7 days ago)
    seven_days_ago = time.time() - (7 * 24 * 60 * 60)
    try:
        resp = client.table("listings").delete().lt("last_seen", seven_days_ago).execute()
        logging.info(f"Deleted {len(resp.data)} stale listings (older than 7 days)")
    except Exception as e:
        logging.error(f"Error deleting stale listings: {e}")


if __name__ == "__main__":
    cleanup()
