# Handoff Report: Platform Scraper Analysis (`synth_arbitrage/scraper.py`)

## 1. Observation
- **Kleinanzeigen Navigation & Structure** (`synth_arbitrage/scraper.py:21-125`):
  - Builds 7–8 sub-queries per brand (e.g. `{brand}-synthesizer`, `{brand}-synth`, `{brand}-drum-machine`, etc.).
  - Executes `page.goto(url, wait_until="domcontentloaded", timeout=20000)` with up to 3 retries per page.
  - Applies random sleep pauses (`2.5-5.5s` before goto, `3.0-6.0s` after goto, `1.0-2.5s` after mouse move/scroll).
  - BeautifulSoup parses `article.aditem`, extracting title (`a.ellipsis`), description (`p.aditem-main--middle--description`), price (`p.aditem-main--middle--price-shipping--price`), and image (`img.imagebox-thumbnail`, upscaled with regex `$_59.JPG`).
  - Context cleanup (`await context.close()` at line 122) is **not** enclosed in a `try...finally` block.
- **eBay DE Navigation & Structure** (`synth_arbitrage/scraper.py:127-181`):
  - Runs a single query per brand: `https://www.ebay.de/sch/i.html?_nkw={brand}+synthesizer&LH_BIN=1&LH_ItemCondition=3000&_ipg=60`.
  - Executes `page.goto(url, wait_until="domcontentloaded", timeout=15000)`.
  - BeautifulSoup parses `a[href*="/itm/"]` within `li` containers, extracting title (class containing `title`), price (class containing `price`), description (empty string `""`), and image (upscaled with regex `s-l500.`).
  - Fully enclosed in `try ... except ... finally:` with `await context.close()` in `finally:`.
  - Does not invoke `stealth_async`.
- **Thomann B-Stock Navigation & Structure** (`synth_arbitrage/scraper.py:183-269`):
  - Scrapes a single global URL (`https://www.thomann.de/de/blowouts_GF_synthesizer.html`).
  - Executes `page.goto(url, wait_until="domcontentloaded", timeout=30000)`.
  - Applies `stealth_async(page)` and mouse move/scroll emulation.
  - BeautifulSoup parses `a.fx-product-box`, title from `div.description`, price from `span.price__primary`, description hardcoded as `"B-Stock from Thomann"`, image from `<picture>` source/img.
  - Pre-filters items by title against `TARGET_BRANDS` before calling `analyze_listing`.
  - Fully enclosed in `try ... except ... finally:` with `await context.close()` in `finally:`.
- **Concurrency & Top-Level Orchestration** (`synth_arbitrage/scraper.py:272-323`):
  - Single `browser = await p.chromium.launch(headless=True)`.
  - `semaphore = asyncio.Semaphore(2)` passed to 24 Kleinanzeigen tasks and 24 eBay tasks.
  - `asyncio.gather(*all_tasks, return_exceptions=True)` executes 49 tasks concurrently.
- **Data Field Passing & `analyze_listing` Output** (`synth_arbitrage/analysis.py:80-228`):
  - Raw price parsed via `extract_price(price_str)`.
  - Cleaned parameters passed to `analyze_listing(title, description, price, url, image_url, source)`.
  - Returns dict with capitalized Spanish keys: `"Modelo"`, `"Estado"`, `"Precio URL"`, `"Precio Mercado"`, `"Ahorro %"`, `"Plataforma"`, `"Enlace"`, `"Imagen"`, `"Reverb"`, `"Mensaje Borrador"`, `"last_seen"`.
- **Diagnostic Key Mismatch** (`diagnostic.py:11-12`):
  - `diagnostic.py` looks for lowercase keys (`'modelo'`, `'precio'`, `'plataforma'`, `'ahorro_porcentaje'`), causing output to print fallback default strings.

## 2. Logic Chain
1. **Navigation Mechanism & Timeout Strategy**:
   - Navigation across all 3 scrapers relies exclusively on `page.goto(url, wait_until="domcontentloaded", timeout=...)` followed by static/random sleep calls.
   - None of the scrapers use Playwright's `wait_for_selector()` or set context default timeouts.
2. **Robustness & Error Isolation**:
   - `scrape_all_platforms()` isolates task failures using `asyncio.gather(..., return_exceptions=True)`.
   - `scrape_ebay_brand` and `scrape_thomann_bstock` properly manage resources via `try...finally` blocks.
   - `scrape_kleinanzeigen_brand` lacks `try...finally` around context closure. An unexpected exception during brand processing can leak Playwright context instances.
3. **Semaphore Lock & Execution Stalls**:
   - `async with semaphore:` in `scrape_kleinanzeigen_brand` locks 1 of the 2 semaphore slots across up to 8 sub-queries x 2 pages x 3 retry attempts x random delays (up to several minutes per brand).
   - If a brand search (e.g. "Simmons") stalls or encounters network retries, it starves other pending brand tasks from acquiring a semaphore slot.
4. **Data Contract Consistency**:
   - `analyze_listing` standardizes evaluation across all 3 scrapers, but returns Spanish capitalized dict keys. `diagnostic.py` uses incorrect lowercase key names when logging results.

## 3. Caveats
- Real network responses and live anti-bot/cloudflare behavior were not tested during this read-only investigation (CODE_ONLY mode).
- Playwright stealth behavior depends on external `playwright_stealth` library presence.

## 4. Conclusion
The platform scraping logic in `synth_arbitrage/scraper.py` is functional but contains key vulnerabilities:
1. **Resource Leak in Kleinanzeigen**: `scrape_kleinanzeigen_brand` lacks a `finally` block for `await context.close()`.
2. **Missing DOM Waiters**: Scrapers rely on fixed sleep delays after `domcontentloaded` instead of `wait_for_selector`.
3. **Semaphore Bottlenecks**: Kleinanzeigen brand tasks hold the shared concurrency semaphore across 7–8 sub-queries, creating long execution delays for subsequent brands.
4. **Key Mismatch in Diagnostic Tool**: `diagnostic.py` reads lowercase keys while `analyze_listing` returns capitalized keys.

## 5. Verification Method
- **File Inspection**:
  - Inspect `synth_arbitrage/scraper.py` lines 43–124 to verify context creation and closure error handling.
  - Inspect `synth_arbitrage/analysis.py` lines 214–226 to verify dictionary keys returned by `analyze_listing`.
  - Inspect `diagnostic.py` line 12 to verify key mismatch.
- **Project Tests**:
  - Run `pytest` to execute existing test suite (e.g., `tests/test_scraper.py`, `tests/test_analysis.py`).
