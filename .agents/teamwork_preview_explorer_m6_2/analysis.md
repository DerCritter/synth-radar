# Analysis Report: Platform Scraper Logic in `synth_arbitrage/scraper.py`

## Executive Summary

This report provides a detailed investigation of the platform-specific web scraping logic implemented in `synth_arbitrage/scraper.py` (covering **Kleinanzeigen**, **eBay DE**, and **Thomann B-Stock**) for Milestone 6.1 of SynthRadar.

---

## 1. Platform-Specific Navigation, Waiting, HTML Fetching, and BeautifulSoup Parsing

### 1.1 Kleinanzeigen Scraper (`scrape_kleinanzeigen_brand`)
- **Navigation Flow**:
  - Creates a new browser context (`viewport={"width": 1280, "height": 800}`, `locale="de-DE"`) and new page. Applies `stealth_async(page)` if stealth library is installed.
  - Dynamically builds up to 7–8 search queries per brand:
    - `{brand}-synthesizer` (scans 2 pages if brand is in `major_brands` ["Roland", "Korg", "Yamaha", "Akai", "Elektron"], 1 page otherwise)
    - `{brand}-synth`, `{brand}-drum-machine`, `{brand}-groovebox`, `{brand}-sampler`, `{brand}-sequencer`, `{brand}-module`
    - `{brand}-eurorack` (except for Yamaha, Casio, Hohner)
  - Target URL format: `https://www.kleinanzeigen.de/s-musikinstrumente/{base_query}/k0c74` (page 1) or `/seite:{page_num}/{base_query}/k0c74` (pages 2+).
  - Navigation uses a 3-attempt retry loop (`attempt in range(3)`).
- **Waiting & Human Emulation**:
  - Pre-navigation random sleep: `2.5` to `5.5` seconds.
  - Navigation call: `await page.goto(url, wait_until="domcontentloaded", timeout=20000)`.
  - Post-navigation random sleep: `3.0` to `6.0` seconds.
  - Human behavior emulation: `page.mouse.move(100..500, 100..500)`, `page.mouse.wheel(0, 300..800)`, followed by an extra `1.0` to `2.5` second sleep.
- **HTML Fetching & BeautifulSoup Parsing**:
  - Fetches page HTML via `content = await page.content()`.
  - Parses with BeautifulSoup (`html.parser`).
  - Container selector: `soup.find_all("article", class_="aditem")`.
  - Card extraction:
    - Title & Href: `ad.find("a", class_="ellipsis")` (prepends `https://www.kleinanzeigen.de`).
    - Description: `ad.find("p", class_="aditem-main--middle--description")`.
    - Price text: `ad.find("p", class_="aditem-main--middle--price-shipping--price")`.
    - Image URL: `ad.find("img", class_="imagebox-thumbnail")` or fallback `ad.find("img")`. Performs regex replace `re.sub(r"\$_\d+\.JPG", "$_59.JPG", image_url)` to fetch higher resolution thumbnail.

### 1.2 eBay DE Scraper (`scrape_ebay_brand`)
- **Navigation Flow**:
  - Single search query per brand: `https://www.ebay.de/sch/i.html?_nkw={brand}+synthesizer&LH_BIN=1&LH_ItemCondition=3000&_ipg=60` (Buy It Now, condition Used, 60 listings per page).
  - Context & Page setup: Creates browser context (`viewport={"width": 1280, "height": 800}`, `locale="de-DE"`) and page.
  - *Note*: Stealth (`stealth_async`) is **NOT** applied to eBay contexts (unlike Kleinanzeigen and Thomann).
- **Waiting & Emulation**:
  - Pre-navigation random sleep: `2.0` to `4.0` seconds.
  - Navigation call: `await page.goto(url, wait_until="domcontentloaded", timeout=15000)`.
  - Post-navigation random sleep: `2.0` to `4.0` seconds.
  - *Note*: No mouse movement or scroll emulation is performed on eBay pages.
- **HTML Fetching & BeautifulSoup Parsing**:
  - Fetches HTML via `content = await page.content()`.
  - Parses with BeautifulSoup (`html.parser`).
  - Link selector: `soup.find_all("a", href=lambda h: h and "/itm/" in h)`. Strips URL parameters using `.split("?")[0]`.
  - Container element: Traverses parent item via `link.find_parent("li")`.
  - Card extraction:
    - Title: `parent.find(class_=lambda c: c and "title" in c)`.
    - Price: `parent.find(class_=lambda c: c and "price" in c)`.
    - Description: Not available on listing grid cards; passed as empty string `""`.
    - Image URL: `parent.find("img")`. Performs regex replace `re.sub(r"s-l\d+\.", "s-l500.", img_url)` to upscale to 500px resolution.

### 1.3 Thomann B-Stock Scraper (`scrape_thomann_bstock`)
- **Navigation Flow**:
  - Single global request scanning Thomann's blowout synth deals: `https://www.thomann.de/de/blowouts_GF_synthesizer.html`.
  - Context & Page setup: Creates context and page. Applies `stealth_async(page)` if available.
- **Waiting & Emulation**:
  - Pre-navigation random sleep: `2.0` to `5.0` seconds.
  - Navigation call: `await page.goto(url, wait_until="domcontentloaded", timeout=30000)`.
  - Post-navigation random sleep: `3.0` to `6.0` seconds.
  - Emulated user interaction: Mouse move (`100..500`), wheel scroll (`300..800`), and `1.0` to `2.0` second pause.
- **HTML Fetching & BeautifulSoup Parsing**:
  - Fetches HTML via `content = await page.content()`.
  - Parses with BeautifulSoup (`html.parser`).
  - Card selector: `soup.find_all("a", class_=lambda c: c and "fx-product-box" in c)`.
  - Card extraction:
    - Title: `card.find("div", class_="description")`, cleaned via `.text.strip().replace("\\n", " ")`.
    - Price text: `card.find("span", class_="price__primary")`.
    - Link: `card.get("href")`, resolved via `urljoin("https://www.thomann.de/de/", link)`.
    - Description: Hardcoded as `"B-Stock from Thomann"`.
    - Image URL: Extracted from `<picture>` tag (`<source type!="image/webp" data-srcset>` or `<img>` `data-src`/`src`). Prepends `https://www.thomann.de` if relative.
  - Brand filtering: Pre-filters item titles against `TARGET_BRANDS` (`if b.lower() in title.lower():`) before evaluating arbitrage qualification.

---

## 2. Timeout Configuration & Handling

| Platform Scraper | `page.goto` Timeout | `wait_for_selector` Timeout | Context Default Timeout Set? | Retry Logic |
| :--- | :--- | :--- | :--- | :--- |
| **Kleinanzeigen** | `20000` ms (20s) | None (0) | No | Up to 3 attempts with 5–10s sleep on failure |
| **eBay DE** | `15000` ms (15s) | None (0) | No | None (single attempt per brand) |
| **Thomann B-Stock** | `30000` ms (30s) | None (0) | No | None (single attempt) |

### Key Observations on Timeouts:
1. **Absence of `wait_for_selector`**: None of the scrapers use explicit DOM element waiting (`wait_for_selector`). They rely solely on `wait_until="domcontentloaded"` followed by `asyncio.sleep()`. If content is rendered asynchronously via JavaScript after DOM content loaded, parsing may run before elements populate.
2. **Missing Context Timeouts**: `browser.new_context()` does not set default navigation timeouts or default execution timeouts.
3. **Kleinanzeigen Cumulative Delays**: Because Kleinanzeigen executes 7–8 queries per brand sequentially with up to 3 retries (each with 20s timeouts + 5–10s retry sleeps), a single blocked or lagging brand search can take **over 2–3 minutes** to execute.

---

## 3. Exception Handling & Concurrency Safety

### 3.1 Task Level (`scrape_all_platforms`)
- The main orchestrator launches all brand tasks via:
  ```python
  results_lists = await asyncio.gather(*all_tasks, return_exceptions=True)
  ```
- `return_exceptions=True` guarantees that an unhandled exception in one brand/platform task does not crash or cancel remaining concurrent tasks. Failed tasks return Exception instances which are logged (`logging.error`).

### 3.2 Subroutine Error Handling & Resource Leak Analysis
- **eBay (`scrape_ebay_brand`)**:
  - Uses `try ... except Exception ... finally:` wrapping context creation, page navigation, and parsing.
  - Context cleanup (`await context.close()`) is inside `finally:`, ensuring browser context resources are freed even on navigation errors.
- **Thomann (`scrape_thomann_bstock`)**:
  - Uses `try ... except Exception ... finally:` with `await context.close()` in `finally:`.
- **Kleinanzeigen (`scrape_kleinanzeigen_brand`) — Resource Leak Defect**:
  - **Defect**: Context creation (`context = await browser.new_context(...)`) and page creation (`page = await context.new_page()`) occur at lines 45–46, but context closure (`await context.close()`) is placed at line 122 **outside of any `try...finally` block**.
  - If an exception occurs outside the inner try blocks (e.g. during query list construction or unexpected page/network errors), `context.close()` will be skipped, leading to **unclosed browser contexts and leaked memory/file handles**.

### 3.3 Semaphore & Concurrency Throttling
- A single `asyncio.Semaphore(2)` is created in `scrape_all_platforms` and shared across 24 Kleinanzeigen tasks and 24 eBay tasks.
- In `scrape_kleinanzeigen_brand`, `async with semaphore:` holds the lock for the entire multi-query brand loop (spanning 7–8 queries and up to ~45 seconds of sleep delays per brand).
- When a brand task like "Simmons" or "Moog" stalls or encounters anti-bot captcha/cloud-flare delays, it occupies 1 of the 2 semaphore slots for a prolonged period, starving other brand tasks waiting in queue.

---

## 4. Extracted Data Fields & Interface Contract with `analyze_listing`

### 4.1 Data Extraction Mapping

| Field | Kleinanzeigen | eBay DE | Thomann B-Stock |
| :--- | :--- | :--- | :--- |
| **Title** | `ad.find("a", class_="ellipsis").text.strip()` | `title_el.text.strip()` | `title_el.text.strip().replace("\n", " ")` |
| **Description** | `desc_elem.text.strip()` (or `""`) | `""` (empty string) | `"B-Stock from Thomann"` |
| **Price (raw)** | `price_elem.text.strip()` | `price_el.text.strip()` | `price_el.text.strip()` |
| **Price (float)** | `extract_price(price_str)` | `extract_price(price_str)` | `extract_price(price_str)` |
| **Listing URL** | `https://www.kleinanzeigen.de` + href | Href without query params | `urljoin("https://www.thomann.de/de/", href)` |
| **Image URL** | `$_59.JPG` upscaled thumbnail | `s-l500.` upscaled thumbnail | Picture source or img src URL |
| **Source** | `"Kleinanzeigen"` | `"eBay"` | `"Thomann B-Stock"` |

### 4.2 Passing Raw Data to `analyze_listing`
Each scraper converts the raw price via `extract_price(...)` and calls `analyze_listing(...)` with position/keyword arguments:

```python
# Kleinanzeigen
analysis = analyze_listing(title, desc, price, link, image_url, source="Kleinanzeigen")

# eBay
opp = analyze_listing(title_el.text.strip(), "", price, href, img_url, source="eBay")

# Thomann B-Stock
analysis = analyze_listing(title, "B-Stock from Thomann", price, link, img_url, source="Thomann B-Stock")
```

### 4.3 `analyze_listing` Output Schema & Key Mismatch in `diagnostic.py`
When an item qualifies, `analyze_listing` returns a dict with capitalized Spanish keys:
```python
{
    "Modelo": detected_model,          # e.g. "Simmons" or "Roland Juno-106"
    "Estado": condition_label,         # e.g. "Funcional (Average)", "Defekt/Bastler", "B-Stock / Oficial"
    "Precio URL": price,               # float, e.g. 450.0
    "Precio Mercado": "450 - 650 €",  # string range
    "Ahorro %": "25%",                 # discount string
    "Plataforma": source,              # string
    "Enlace": url,                     # string
    "Imagen": image_url,               # string
    "Reverb": reverb_url,              # string
    "Mensaje Borrador": msg,           # string draft German message
    "last_seen": timestamp,            # float
}
```

**Diagnostic Key Mismatch Finding**:
In `diagnostic.py` (lines 11–12), output logging attempts to extract lower-case keys:
```python
o.get('modelo', 'Unknown') | o.get('precio', 0)€ | o.get('plataforma', 'N/A') | o.get('ahorro_porcentaje', '0%')
```
Because `analyze_listing` returns capitalized keys (`"Modelo"`, `"Precio URL"`, `"Plataforma"`, `"Ahorro %"`), `diagnostic.py` displays default fallbacks (`Unknown | 0€ | N/A | 0%`) for all detected opportunities.
