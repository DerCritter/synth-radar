"""Scraper module for SynthRadar arbitrage system.

Provides asynchronous web scraping routines targeting Kleinanzeigen, eBay DE,
and Thomann B-Stock using Playwright and BeautifulSoup4.
"""

import asyncio
import logging
import random
import re
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from synth_arbitrage.analysis import analyze_listing, extract_price
from synth_arbitrage.config import TARGET_BRANDS


async def scrape_kleinanzeigen_brand(
    brand: str,
    browser: Any,
    major_brands: List[str],
    seen_links: Set[str],
    stealth_async: Any,
    semaphore: asyncio.Semaphore
) -> List[Dict[str, Any]]:
    """Scrapes Kleinanzeigen listings for a specific brand asynchronously.

    Args:
        brand: Brand name to search for.
        browser: Playwright Browser instance.
        major_brands: List of major brand names to determine pagination depth.
        seen_links: Set of already processed listing URLs to avoid duplicates.
        stealth_async: Stealth function for Playwright evasion.
        semaphore: Asyncio Semaphore for concurrency limits.

    Returns:
        List of analyzed opportunity dictionaries.
    """
    results: List[Dict[str, Any]] = []
    async with semaphore:
        logging.info(f"--- Iniciando escaneo de marca: {brand} (Kleinanzeigen) ---")
        context = await browser.new_context(viewport={"width": 1280, "height": 800}, locale="de-DE")
        page = await context.new_page()

        if stealth_async:
            await stealth_async(page)

        queries = [
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
                        logging.warning(f"Timeout/error cargando {url} (Intento {attempt + 1}/3): {e}")
                        if attempt == 2:
                            continue
                        await asyncio.sleep(random.uniform(5.0, 10.0))

                try:
                    content = await page.content()
                    soup = BeautifulSoup(content, "html.parser")
                    ads = soup.find_all("article", class_="aditem")
                    logging.info(f"[{search_display} p{page_num}] Encontrados {len(ads)} anuncios.")

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

                        img_elem = ad.find("img", class_="imagebox-thumbnail")
                        if not img_elem:
                            img_elem = ad.find("img")
                        image_url = img_elem.get("src", "") if img_elem else ""
                        if image_url:
                            image_url = re.sub(r"\$_\d+\.JPG", "$_59.JPG", image_url, flags=re.IGNORECASE)

                        price = extract_price(price_str)
                        analysis = analyze_listing(title, desc, price, link, image_url, source="Kleinanzeigen")

                        if analysis and link not in seen_links:
                            seen_links.add(link)
                            results.append(analysis)
                except Exception as e:
                    logging.error(f"Error procesando página {url}: {e}")

        await context.close()
        await asyncio.sleep(random.uniform(4.0, 8.0))
    return results


async def scrape_ebay_brand(
    brand: str,
    page: Any,
    seen_links: Set[str]
) -> List[Dict[str, Any]]:
    """Scrapes eBay DE listings for a specific brand asynchronously.

    Args:
        brand: Target brand string.
        page: Playwright Page instance.
        seen_links: Set of seen URLs to prevent duplicated output.

    Returns:
        List of opportunity dictionaries found on eBay.
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
                    img_url = parent.find("img").get("src", "") if parent.find("img") else ""
                    if img_url:
                        img_url = re.sub(r"s-l\d+\.", "s-l500.", img_url, flags=re.IGNORECASE)
                    opp = analyze_listing(title_el.text.strip(), "", price, href, img_url, source="eBay")
                    if opp:
                        results.append(opp)
    except Exception as e:
        logging.error(f"Error parseando tarjeta de eBay para {brand}: {e}")
    return results


async def scrape_thomann_bstock(
    browser: Any,
    stealth_async: Any
) -> List[Dict[str, Any]]:
    """Scrapes Thomann B-Stock deals section for target synth equipment.

    Args:
        browser: Playwright Browser instance.
        stealth_async: Playwright stealth helper function.

    Returns:
        List of qualifying Thomann B-Stock opportunity dicts.
    """
    logging.info("Iniciando escaneo de Thomann B-Stock (Stealth)...")
    results: List[Dict[str, Any]] = []

    try:
        context = await browser.new_context(viewport={"width": 1280, "height": 800}, locale="de-DE")
        page = await context.new_page()
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

        logging.info(f"[Thomann B-Stock] Encontrados {len(cards)} anuncios.")

        for card in cards:
            title_el = card.find("div", class_="description")
            if not title_el:
                continue

            title = title_el.text.strip().replace("\\n", " ")

            price_el = card.find("span", class_="price__primary")
            if not price_el:
                continue

            link = card.get("href")
            if link:
                link = urljoin("https://www.thomann.de/de/", link)

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

            brand_match = False
            for b in TARGET_BRANDS:
                if b.lower() in title.lower():
                    brand_match = True
                    break

            if brand_match:
                analysis = analyze_listing(title, "B-Stock from Thomann", price, link, img_url, source="Thomann B-Stock")
                if analysis:
                    results.append(analysis)

    except Exception as e:
        logging.error(f"Error en Thomann B-Stock: {e}")
    finally:
        await context.close()

    return results


async def scrape_all_platforms() -> List[Dict[str, Any]]:
    """Orchestrates multi-platform async web scraping across Kleinanzeigen, eBay, and Thomann.

    Launches Playwright chromium browser with stealth configurations and aggregates
    opportunity results from all scrapers.

    Returns:
        Aggregated list of all discovered opportunity dictionaries.
    """
    logging.info("Iniciando escaneo en kleinanzeigen.de y ebay.de con Playwright (STEALTH MODE)...")
    all_results: List[Dict[str, Any]] = []

    try:
        from playwright_stealth import stealth_async
    except ImportError:
        stealth_async = None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        try:
            seen_links: Set[str] = set()
            major_brands = ["Roland", "Korg", "Yamaha", "Akai", "Elektron"]
            semaphore = asyncio.Semaphore(2)

            kleinanzeigen_tasks = [
                scrape_kleinanzeigen_brand(brand, browser, major_brands, seen_links, stealth_async, semaphore)
                for brand in TARGET_BRANDS
            ]

            ebay_context = await browser.new_context(viewport={"width": 1280, "height": 800}, locale="de-DE")
            ebay_page = await ebay_context.new_page()

            ebay_tasks = [
                scrape_ebay_brand(brand, ebay_page, seen_links)
                for brand in TARGET_BRANDS
            ]

            thomann_task = [scrape_thomann_bstock(browser, stealth_async)]

            all_tasks = kleinanzeigen_tasks + ebay_tasks + thomann_task
            results_lists = await asyncio.gather(*all_tasks, return_exceptions=True)

            for res in results_lists:
                if isinstance(res, list):
                    all_results.extend(res)
                elif isinstance(res, Exception):
                    logging.error(f"Task failed with exception: {res}")

            await ebay_context.close()

        except Exception as e:
            logging.error(f"Error durante el scraping: {e}")
        finally:
            await browser.close()

    return all_results
