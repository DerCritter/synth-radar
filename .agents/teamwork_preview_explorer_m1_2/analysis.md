# SynthRadar Refactoring & Testing — Explorer 2 Technical Analysis

**Author:** Explorer 2  
**Target Scope:** Web Scraping (`scrape_*`), Database Operations (`SupabaseDB`), and Main Entry Point (`main_async`, `main`)  
**Project:** SynthRadar Refactoring & Testing (Milestone 1)  
**Date:** 2026-07-29  

---

## Executive Summary

This report presents a thorough investigation of the Web Scraping functions, Database Operations, and Main Entry Point within `synth_arbitrage.py` and `supabase_client.py`. We provide a modular breakdown blueprint separating scraping logic into `synth_arbitrage/scraper.py`, database operations into `synth_arbitrage/database.py`, and preserving `synth_arbitrage.py` as a fully backward-compatible executable CLI entry point. Explicit Python type hints, Google-style docstrings, and interface contracts are specified.

---

## 1. Analysis of Existing Codebase Components

### 1.1 Web Scraping Functions (`synth_arbitrage.py`)

#### `scrape_kleinanzeigen_brand` (Lines 318–401)
* **Purpose:** Scrapes eBay Kleinanzeigen (kleinanzeigen.de) for a specific synthesizer brand across multiple category search queries (`brand-synthesizer`, `brand-synth`, `brand-drum-machine`, etc.).
* **Concurrency & Stealth:**
  * Uses an `asyncio.Semaphore(2)` to cap concurrent brand scraping tasks.
  * Spawns Playwright BrowserContext with German locale (`de-DE`) and desktop viewport (`1280x800`).
  * Applies `playwright_stealth` if available.
  * Simulates mouse movement and wheel scrolling to bypass basic anti-bot heuristics.
* **Pagination & Retries:**
  * Retries up to 3 times per query page with randomized backoff delays (2.5s–10.0s).
  * Major brands (`Roland`, `Korg`, `Yamaha`, `Akai`, `Elektron`) scan 2 pages for `brand-synthesizer`, while secondary brands scan 1 page.
* **HTML Parsing & Extraction:**
  * Parses DOM with `bs4.BeautifulSoup`.
  * Extracts ad articles (`article.aditem`), listing link (`a.ellipsis`), title, description, price string, and thumbnail image.
  * Transforms thumbnail image regex (`$_\d+.JPG`) to high-resolution variant (`$_59.JPG`).
  * Delegates price parsing to `extract_price()` and business rules to `analyze_listing()`.
* **Identified Refactoring Issues:**
  * Coupled directly to global `TARGET_BRANDS` and inline `extract_price`/`analyze_listing`.
  * Lacks Python type annotations and standard docstrings.

#### `scrape_ebay_brand` (Lines 403–433)
* **Purpose:** Scrapes eBay Germany (`ebay.de`) search results for buy-it-now (`LH_BIN=1`) used items (`LH_ItemCondition=3000`).
* **Execution Model:**
  * Shares a single Playwright context and page across tasks.
  * Parses HTML for `/itm/` links, strips tracking query params, and extracts title, price, and thumbnail image (`s-l500.jpg`).
* **Identified Refactoring Issues:**
  * Accepts a single `Page` instance which can create concurrent navigation conflicts if called asynchronously across multiple brands without page isolation or sequential execution.
  * Error handling logs failures per brand but does not clean up individual page states.

#### `scrape_thomann_bstock` (Lines 435–510)
* **Purpose:** Scrapes official Thomann B-Stock blowout deals (`thomann.de/de/blowouts_GF_synthesizer.html`).
* **Execution Model:**
  * Spawns a separate browser context with stealth options.
  * Extracts product card boxes (`a.fx-product-box`), primary price, and high-res image sources.
  * Matches brand names against `TARGET_BRANDS`.
  * Sets opportunity condition `estado` to `'B-Stock / Oficial'`.
* **Identified Refactoring Issues:**
  * Hardcoded brand checks inline rather than using modular helpers.

#### `scrape_all_platforms` (Lines 512–560)
* **Purpose:** Top-level async orchestrator for all scraping tasks.
* **Execution Model:**
  * Manages Playwright lifecycle (`async_playwright()`).
  * Launches single chromium browser instance.
  * Assembles `kleinanzeigen_tasks`, `ebay_tasks`, and `thomann_task`.
  * Uses `asyncio.gather(*all_tasks, return_exceptions=True)` to execute concurrently.
* **Identified Refactoring Issues:**
  * Hardcoded list of `major_brands`.
  * Hardcoded semaphore limit (2).
  * Direct dependency on top-level configuration constants.

---

### 1.2 Database Operations (`supabase_client.py`)

#### `SupabaseDB` (Lines 1–73)
* **Initialization:** Reads `SUPABASE_URL` and `SUPABASE_KEY` from `os.environ`. If unconfigured, logs a warning and sets `self.client = None`.
* **Schema Mapping:**
  * `_map_to_db(item)`: Translates internal Spanish application keys (`"Enlace"`, `"Modelo"`, `"Precio URL"`, `"Ahorro %"`, `"last_seen"`, etc.) to Supabase table column names (`"url"`, `"modelo"`, `"precio"`, `"ahorro_porcentaje"`, etc.).
  * `_map_from_db(item)`: Translates DB column names back to internal application keys.
* **Methods:**
  * `upsert_listings(listings_list)`: Bulk upserts mapped records using `url` as primary key.
  * `get_listings()`: Fetches all records from table `"listings"` and maps back to application dict format.
* **Identified Refactoring Issues:**
  * No Python type hints or docstrings.
  * No custom error handling or local fallback persistence mode when `SUPABASE_URL` is missing.
  * Used by `cleanup_supabase.py` via `from supabase_client import SupabaseDB`. Must retain backward-compatible import shim!

---

### 1.3 Main Entry Point & Orchestration (`synth_arbitrage.py`)

* **Current `main_async` & `main` (Lines 562–582):**
  ```python
  async def main_async():
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

  def main():
      asyncio.run(main_async())

  if __name__ == "__main__":
      main()
  ```
* **Workflow / CI Requirements:**
  * `.github/workflows/scraper.yml` executes `python synth_arbitrage.py`.
  * `synth_arbitrage.py` MUST remain directly executable without modifying CI configuration.

---

## 2. Proposed Modular Architecture Breakdown

To cleanly segregate responsibilities across the application while fulfilling M1 refactoring blueprints, we structure the `synth_arbitrage/` package as follows:

```
synth-radar/
├── synth_arbitrage/                # Package root directory
│   ├── __init__.py                # Package init & re-exports
│   ├── config.py                  # Configuration, constants & market values (Explorer 1)
│   ├── analysis.py                # Price extraction & listing analysis (Explorer 1)
│   ├── scraper.py                 # Scraper functions with Playwright & BeautifulSoup (Explorer 2)
│   └── database.py                # SupabaseDB class & database operations (Explorer 2)
├── synth_arbitrage.py              # Main CLI entry point & backward-compatibility facade
├── supabase_client.py              # Backward-compatibility wrapper for SupabaseDB
└── tests/                         # Pytest unit & integration test suite (Explorer 3)
```

---

## 3. Detailed Specifications & Code Contracts

### 3.1 `synth_arbitrage/scraper.py`

Below is the complete module design for `synth_arbitrage/scraper.py`, including explicit Python type annotations, imports, and docstrings.

```python
"""Web scraping module for SynthRadar.

Provides async scraper functions for Kleinanzeigen.de, eBay.de, and Thomann B-Stock
using Playwright and BeautifulSoup.
"""

import asyncio
import logging
import random
import re
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from bs4 import BeautifulSoup
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from synth_arbitrage.analysis import analyze_listing, extract_price
from synth_arbitrage.config import TARGET_BRANDS, load_or_create_config

logger = logging.getLogger(__name__)


async def scrape_kleinanzeigen_brand(
    brand: str,
    browser: Browser,
    major_brands: List[str],
    seen_links: Set[str],
    stealth_async: Optional[Callable[[Page], Any]] = None,
    semaphore: Optional[asyncio.Semaphore] = None,
) -> List[Dict[str, Any]]:
    """Scrapes Kleinanzeigen.de listings for a specific synth brand.

    Args:
        brand: Name of the synth brand to search for (e.g. 'Roland').
        browser: Active Playwright Browser instance.
        major_brands: List of major brands receiving multi-page depth scanning.
        seen_links: Shared set of scraped URLs for deduplication across queries.
        stealth_async: Optional stealth function to apply to new pages.
        semaphore: Optional concurrency limit semaphore.

    Returns:
        List of analyzed listing dictionaries meeting arbitrage criteria.
    """
    results: List[Dict[str, Any]] = []
    
    # Use provided semaphore or dummy context
    sem_context = semaphore if semaphore else asyncio.Semaphore(10)
    
    async with sem_context:
        logger.info(f"--- Iniciando escaneo de marca: {brand} (Kleinanzeigen) ---")
        context: BrowserContext = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="de-DE"
        )
        page: Page = await context.new_page()
        
        if stealth_async:
            await stealth_async(page)

        queries: List[Tuple[str, int]] = [
            (f"{brand}-synthesizer", 2 if brand in major_brands else 1),
            (f"{brand}-synth", 1),
            (f"{brand}-drum-machine", 1),
            (f"{brand}-groovebox", 1),
            (f"{brand}-sampler", 1),
            (f"{brand}-sequencer", 1),
            (f"{brand}-module", 1),
        ]
        if brand not in ["Yamaha", "Casio", "Hohner"]:
            queries.append((f"{brand}-eurorack", 1))

        for base_query, pages in queries:
            for page_num in range(1, pages + 1):
                search_display = base_query.replace("-", " ").title()
                if page_num == 1:
                    url = f"https://www.kleinanzeigen.de/s-musikinstrumente/{base_query}/k0c74"
                else:
                    url = f"https://www.kleinanzeigen.de/s-musikinstrumente/seite:{page_num}/{base_query}/k0c74"
                
                for attempt in range(3):
                    try:
                        await asyncio.sleep(random.uniform(2.5, 5.5))
                        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                        await asyncio.sleep(random.uniform(3.0, 6.0))
                        
                        await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
                        await page.mouse.wheel(0, random.randint(300, 800))
                        await asyncio.sleep(random.uniform(1.0, 2.5))
                        break
                    except Exception as e:
                        logger.warning(f"Timeout/error cargando {url} (Intento {attempt + 1}/3): {e}")
                        if attempt == 2:
                            continue
                        await asyncio.sleep(random.uniform(5.0, 10.0))
                
                try:
                    content = await page.content()
                    soup = BeautifulSoup(content, "html.parser")
                    ads = soup.find_all("article", class_="aditem")
                    logger.info(f"[{search_display} p{page_num}] Encontrados {len(ads)} anuncios.")
                    
                    for ad in ads:
                        title_elem = ad.find("a", class_="ellipsis")
                        desc_elem = ad.find("p", class_="aditem-main--middle--description")
                        price_elem = ad.find("p", class_="aditem-main--middle--price-shipping--price")
                        
                        if not title_elem or not price_elem:
                            continue
                            
                        title = title_elem.text.strip()
                        link = "https://www.kleinanzeigen.de" + title_elem["href"]
                        desc = desc_elem.text.strip() if desc_elem else ""
                        price_str = price_elem.text.strip()
                        
                        img_elem = ad.find("img", class_="imagebox-thumbnail") or ad.find("img")
                        image_url = img_elem.get("src", "") if img_elem else ""
                        if image_url:
                            image_url = re.sub(r"\$_\d+\.JPG", "$_59.JPG", image_url, flags=re.IGNORECASE)
                        
                        price = extract_price(price_str)
                        analysis = analyze_listing(title, desc, price, link, image_url, source="Kleinanzeigen")
                        
                        if analysis and link not in seen_links:
                            seen_links.add(link)
                            results.append(analysis)
                except Exception as e:
                    logger.error(f"Error procesando página {url}: {e}")
        
        await context.close()
        await asyncio.sleep(random.uniform(4.0, 8.0))
        
    return results


async def scrape_ebay_brand(
    brand: str,
    page: Page,
    seen_links: Set[str],
) -> List[Dict[str, Any]]:
    """Scrapes eBay.de search results for a specific synth brand.

    Args:
        brand: Synth brand name to search on eBay.
        page: Shared Playwright Page instance.
        seen_links: Shared set of processed listing URLs for deduplication.

    Returns:
        List of analyzed listing dictionaries meeting arbitrage criteria.
    """
    results: List[Dict[str, Any]] = []
    url = f"https://www.ebay.de/sch/i.html?_nkw={brand}+synthesizer&LH_BIN=1&LH_ItemCondition=3000&_ipg=60"
    
    try:
        await asyncio.sleep(random.uniform(2.0, 4.0))
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        await asyncio.sleep(random.uniform(2.0, 4.0))
        
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")
        
        for link in soup.find_all("a", href=lambda h: h and "/itm/" in h):
            href = link.get("href").split("?")[0]
            if href in seen_links:
                continue
            seen_links.add(href)
            
            parent = link.find_parent("li")
            if parent:
                title_el = parent.find(class_=lambda c: c and "title" in c)
                price_el = parent.find(class_=lambda c: c and "price" in c)
                
                if title_el and price_el:
                    price = extract_price(price_el.text.strip())
                    img_elem = parent.find("img")
                    img_url = img_elem.get("src", "") if img_elem else ""
                    if img_url:
                        img_url = re.sub(r"s-l\d+\.", "s-l500.", img_url, flags=re.IGNORECASE)
                    
                    opp = analyze_listing(title_el.text.strip(), "", price, href, img_url, source="eBay")
                    if opp:
                        results.append(opp)
    except Exception as e:
        logger.error(f"Error parseando tarjeta de eBay para {brand}: {e}")
        
    return results


async def scrape_thomann_bstock(
    browser: Browser,
    stealth_async: Optional[Callable[[Page], Any]] = None,
    target_brands: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Scrapes Thomann B-Stock synthesizer blowout listings.

    Args:
        browser: Active Playwright Browser instance.
        stealth_async: Optional stealth function to apply to page.
        target_brands: Optional brand list filter (defaults to TARGET_BRANDS).

    Returns:
        List of analyzed B-Stock listing dictionaries.
    """
    logger.info("Iniciando escaneo de Thomann B-Stock (Stealth)...")
    results: List[Dict[str, Any]] = []
    brands_to_match = target_brands if target_brands is not None else TARGET_BRANDS

    context: BrowserContext = await browser.new_context(
        viewport={"width": 1280, "height": 800},
        locale="de-DE"
    )
    try:
        page: Page = await context.new_page()
        if stealth_async:
            await stealth_async(page)
            
        url = "https://www.thomann.de/de/blowouts_GF_synthesizer.html"
        
        await asyncio.sleep(random.uniform(2.0, 5.0))
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(random.uniform(3.0, 6.0))
        
        await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
        await page.mouse.wheel(0, random.randint(300, 800))
        await asyncio.sleep(random.uniform(1.0, 2.0))
        
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")
        cards = soup.find_all("a", class_=lambda c: c and "fx-product-box" in c)
        
        logger.info(f"[Thomann B-Stock] Encontrados {len(cards)} anuncios.")
        
        for card in cards:
            title_el = card.find("div", class_="description")
            if not title_el:
                continue
            
            title = title_el.text.strip().replace("\n", " ")
            price_el = card.find("span", class_="price__primary")
            if not price_el:
                continue
            
            link = card.get("href")
            if link and not link.startswith("http"):
                link = "https://www.thomann.de/de/" + link
                
            price_str = price_el.text.strip()
            price = extract_price(price_str)
            
            img_el = card.find("picture")
            img_url = ""
            if img_el:
                source = img_el.find("source", type=lambda t: t != "image/webp")
                if source and source.get("data-srcset"):
                    img_url = source.get("data-srcset").split(",")[0].strip().split(" ")[0]
                else:
                    img_src = img_el.find("img")
                    if img_src:
                        img_url = img_src.get("data-src") or img_src.get("src")
            
            if img_url and not img_url.startswith("http"):
                img_url = "https://www.thomann.de" + img_url
            
            brand_match = any(b.lower() in title.lower() for b in brands_to_match)
            if brand_match:
                analysis = analyze_listing(title, "B-Stock from Thomann", price, link, img_url, source="Thomann B-Stock")
                if analysis:
                    analysis["estado"] = "B-Stock / Oficial"
                    results.append(analysis)
                    
    except Exception as e:
        logger.error(f"Error en Thomann B-Stock: {e}")
    finally:
        await context.close()
        
    return results


async def scrape_all_platforms(
    target_brands: Optional[List[str]] = None,
    headless: bool = True,
) -> List[Dict[str, Any]]:
    """Orchestrates multi-platform scraping across Kleinanzeigen, eBay, and Thomann B-Stock.

    Args:
        target_brands: List of brands to scan (defaults to TARGET_BRANDS).
        headless: Whether to launch Chromium in headless mode. Defaults to True.

    Returns:
        Combined list of all valid synth arbitrage opportunities discovered.
    """
    logger.info("Iniciando escaneo en kleinanzeigen.de y ebay.de con Playwright (STEALTH MODE)...")
    all_results: List[Dict[str, Any]] = []
    brands_to_scan = target_brands if target_brands is not None else TARGET_BRANDS
    
    try:
        from playwright_stealth import stealth_async
    except ImportError:
        stealth_async = None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        
        try:
            seen_links: Set[str] = set()
            major_brands = ["Roland", "Korg", "Yamaha", "Akai", "Elektron"]
            semaphore = asyncio.Semaphore(2)

            kleinanzeigen_tasks = [
                scrape_kleinanzeigen_brand(brand, browser, major_brands, seen_links, stealth_async, semaphore)
                for brand in brands_to_scan
            ]
            
            ebay_context = await browser.new_context(viewport={"width": 1280, "height": 800}, locale="de-DE")
            ebay_page = await ebay_context.new_page()
            
            ebay_tasks = [
                scrape_ebay_brand(brand, ebay_page, seen_links)
                for brand in brands_to_scan
            ]
            
            thomann_task = [scrape_thomann_bstock(browser, stealth_async, brands_to_scan)]
            
            all_tasks = kleinanzeigen_tasks + ebay_tasks + thomann_task
            results_lists = await asyncio.gather(*all_tasks, return_exceptions=True)
            
            for res in results_lists:
                if isinstance(res, list):
                    all_results.extend(res)
                elif isinstance(res, Exception):
                    logger.error(f"Task failed with exception: {res}")
            
            await ebay_context.close()
            
        except Exception as e:
            logger.error(f"Error durante el scraping: {e}")
        finally:
            await browser.close()
            
    return all_results
```

---

### 3.2 `synth_arbitrage/database.py`

Below is the complete module design for `synth_arbitrage/database.py`.

```python
"""Database operations module for SynthRadar.

Handles interactions with Supabase, including data mapping, upserts,
and listings retrieval.
"""

import logging
import os
from typing import Any, Dict, List, Optional

try:
    from supabase import Client, create_client
except ImportError:
    Client = Any  # Type fallback if supabase is not installed
    create_client = None

logger = logging.getLogger(__name__)


class SupabaseDB:
    """Handles persistence and querying of synth arbitrage listings in Supabase DB."""

    def __init__(self, url: Optional[str] = None, key: Optional[str] = None) -> None:
        """Initializes SupabaseDB client from provided parameters or environment variables.

        Args:
            url: Supabase URL string. Defaults to SUPABASE_URL env var.
            key: Supabase API Key string. Defaults to SUPABASE_KEY env var.
        """
        self.url: Optional[str] = url or os.environ.get("SUPABASE_URL")
        self.key: Optional[str] = key or os.environ.get("SUPABASE_KEY")
        self.client: Optional[Client] = None

        if not self.url or not self.key:
            logger.warning("SUPABASE_URL or SUPABASE_KEY not set. Supabase client won't work correctly.")
        elif create_client is not None:
            try:
                self.client = create_client(self.url, self.key)
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")

    def _map_to_db(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Maps internal application listing dictionary to database table schema.

        Args:
            item: Internal listing dictionary.

        Returns:
            Dictionary mapped to database column names.
        """
        return {
            "url": item.get("Enlace"),
            "modelo": item.get("Modelo"),
            "estado": item.get("Estado"),
            "precio": item.get("Precio URL"),
            "precio_mercado": item.get("Precio Mercado"),
            "ahorro_porcentaje": item.get("Ahorro %"),
            "plataforma": item.get("Plataforma"),
            "imagen": item.get("Imagen"),
            "reverb": item.get("Reverb"),
            "mensaje_borrador": item.get("Mensaje Borrador"),
            "last_seen": item.get("last_seen"),
            "fecha_agregado": item.get("Fecha Agregado"),
        }

    def _map_from_db(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Maps database record dictionary to internal application representation.

        Args:
            item: Database row dictionary.

        Returns:
            Internal listing dictionary with Spanish key names.
        """
        return {
            "Enlace": item.get("url"),
            "Modelo": item.get("modelo"),
            "Estado": item.get("estado"),
            "Precio URL": item.get("precio"),
            "Precio Mercado": item.get("precio_mercado"),
            "Ahorro %": item.get("ahorro_porcentaje"),
            "Plataforma": item.get("plataforma"),
            "Imagen": item.get("imagen"),
            "Reverb": item.get("reverb"),
            "Mensaje Borrador": item.get("mensaje_borrador"),
            "last_seen": item.get("last_seen"),
            "Fecha Agregado": item.get("fecha_agregado"),
        }

    def upsert_listings(self, listings_list: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        """Upserts a list of listing opportunities to the 'listings' table.

        Args:
            listings_list: List of internal listing dictionaries.

        Returns:
            List of upserted database records if successful, or None on failure/unconfigured DB.
        """
        if not self.client:
            return None

        if not listings_list:
            return []

        db_items = [self._map_to_db(item) for item in listings_list]
        try:
            response = self.client.table("listings").upsert(db_items).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error upserting listings to Supabase: {e}")
            return None

    def get_listings(self) -> List[Dict[str, Any]]:
        """Retrieves all listing records from the 'listings' table.

        Returns:
            List of internal listing dictionaries, or empty list on failure.
        """
        if not self.client:
            return []

        try:
            response = self.client.table("listings").select("*").execute()
            return [self._map_from_db(item) for item in response.data]
        except Exception as e:
            logger.error(f"Error getting listings from Supabase: {e}")
            return []
```

---

### 3.3 Main Entry Point Refactoring (`synth_arbitrage.py`)

`synth_arbitrage.py` at repository root acts as both the main CLI entry point for GitHub Actions (`python synth_arbitrage.py`) and a backward-compatible facade re-exporting key submodules.

```python
"""SynthRadar main entry point and legacy facade.

Executes synth arbitrage scraping and upserts results to Supabase DB.
Provides backward compatibility for existing imports and automated CI runners.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List

# Re-exports from submodules for backward compatibility
from synth_arbitrage.config import (
    TARGET_BRANDS,
    MARKET_VALUES,
    JUNK_KEYWORDS,
    ACCESSORY_KEYWORDS,
    DEFECTIVE_KEYWORDS,
    CONDITION_DEFEKT,
    CONDITION_MINT,
    CONDITION_POOR,
    CONDITION_IGNORE,
    load_or_create_config,
)
from synth_arbitrage.analysis import (
    extract_price,
    get_market_price,
    analyze_listing,
)
from synth_arbitrage.database import SupabaseDB
from synth_arbitrage.scraper import (
    scrape_kleinanzeigen_brand,
    scrape_ebay_brand,
    scrape_thomann_bstock,
    scrape_all_platforms,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


async def main_async() -> None:
    """Asynchronous entry point for synth arbitrage scraping workflow."""
    print("🤖 Iniciando Bot Experto en Arbitraje de Sintetizadores (Cloud Version)...")

    opportunities: List[Dict[str, Any]] = await scrape_all_platforms()

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
    """Synchronous entry point called by command line execution."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
```

---

### 3.4 `supabase_client.py` Backward-Compatibility Shim

To preserve compatibility with helper scripts like `cleanup_supabase.py`:

```python
"""Backward-compatibility module shim for Supabase client operations."""

from synth_arbitrage.database import SupabaseDB

__all__ = ["SupabaseDB"]
```

---

## 4. Verification & Testing Method

1. **Syntax & Import Invariant Verification:**
   * Run `python -m py_compile synth_arbitrage.py` and `python -m py_compile supabase_client.py`.
   * Verify imports: `python -c "from synth_arbitrage.scraper import scrape_all_platforms; from synth_arbitrage.database import SupabaseDB; print('Imports successful')"`
2. **Backward Compatibility Check:**
   * Run `python -c "from supabase_client import SupabaseDB; from synth_arbitrage import scrape_kleinanzeigen_brand; print('Legacy imports valid')"`
   * Run `python -c "from cleanup_supabase import main"` to verify no broken imports in utility scripts.
3. **Execution Check:**
   * Execute `python synth_arbitrage.py` (with or without `SUPABASE_URL`/`SUPABASE_KEY` env vars set) to ensure execution completes cleanly.

---

## 5. Summary of Recommendations for Implementation Phase (M2)

1. Create package directory `synth_arbitrage/` with `__init__.py`.
2. Extract DB logic into `synth_arbitrage/database.py` with type annotations and docstrings.
3. Extract Scraper logic into `synth_arbitrage/scraper.py` with type annotations, docstrings, and parameterized brand inputs.
4. Update `synth_arbitrage.py` to import from submodules and serve as the clean top-level CLI entry point.
5. Create `supabase_client.py` shim re-exporting `SupabaseDB`.
