# Exploration & Root Cause Analysis Report — Scraper Freeze After "Simmons"

**Milestone**: M6.1 — Exploration & Root Cause Analysis  
**Agent**: Explorer 1 (`teamwork_preview_explorer_m6_1`)  
**Target Workspace**: `/Users/dacritter/.gemini/antigravity/playground/pulsing-perseverance`  
**Date**: 2026-07-30  

---

## Executive Summary

This report presents a comprehensive investigation into the root causes of the Python Playwright + BeautifulSoup web scraper hanging/freezing during execution, specifically after processing the brand **"Simmons"** in `diagnostic.py` and `synth_arbitrage/scraper.py`.

### Key Findings:
1. **"Simmons" Position**: "Simmons" is the **24th and final brand** (index 23 out of 24) in `TARGET_BRANDS` (`synth_arbitrage/config.py:51-56`). Because brand scraping tasks are queued sequentially into `asyncio.gather()`, "Simmons" is the last brand processed in both Kleinanzeigen and eBay scraping pools. "Hanging after Simmons" corresponds to the exit phase of `asyncio.gather()` when all brand scraping coroutines finish or time out and `scrape_all_platforms()` attempts to close the Playwright browser and shut down the Playwright driver process context manager.
2. **Playwright Resource Lifecycle & Context Leaks**:
   - `scrape_kleinanzeigen_brand` (`synth_arbitrage/scraper.py:21-124`) creates a `BrowserContext` and `Page` per brand, but calls `await context.close()` at line 122 **WITHOUT a `try ... finally` block**. Any unhandled exception during scraping (navigation timeouts, network drops, stealth script issues) skips `context.close()`, causing browser contexts and pages to leak in memory.
   - `page.close()` is **never** explicitly called anywhere across the entire codebase (`scraper.py`).
3. **Freeze / Deadlock Mechanism (Multi-Factorial)**:
   - **Playwright Driver Transport Deadlock**: Exiting `async with async_playwright() as p:` (`scraper.py:289`) after calling `await browser.close()` (`scraper.py:321`) hangs when leaked contexts, background Chrome DevTools Protocol (CDP) handlers (injected by `playwright_stealth`), or open websockets keep event loop futures active. Python's `asyncio.run()` in `diagnostic.py:17` waits indefinitely for pending transport tasks to close.
   - **Semaphore Misuse (`asyncio.sleep` held inside semaphore)**: In both `scrape_kleinanzeigen_brand` (line 123) and `scrape_ebay_brand` (line 179), `await asyncio.sleep(...)` is called **INSIDE** the `async with semaphore:` block. This keeps the semaphore lock acquired for 4-8 seconds per brand while doing nothing, causing severe lock contention across the 48 brand coroutines sharing `Semaphore(2)`.
   - **Lack of Timeouts**: There are no global timeouts on `scrape_all_platforms()`, no per-task timeouts in `asyncio.gather()`, and high individual navigation timeouts (up to 20s * 3 retries = 60s per page * 8 queries = up to 800s per brand).

---

## Detailed Investigation Answers

### Question 1: Brand Iteration Flow & "Simmons" Position

#### 1.1 `diagnostic.py` Execution Flow
`diagnostic.py` serves as the CLI diagnostic entrypoint. It executes:
```python
# diagnostic.py:7-17
async def main():
    print("Iniciando prueba diagnóstica del scraper...")
    opportunities = await scrape_all_platforms()
    ...

if __name__ == "__main__":
    asyncio.run(main())
```
`diagnostic.py` delegates all scraping, browser creation, task orchestration, and cleanup to `scrape_all_platforms()` in `synth_arbitrage/scraper.py`.

#### 1.2 Brand Definition and Position
Target brands are defined in `synth_arbitrage/config.py:51-56`:
```python
TARGET_BRANDS: List[str] = [
    "Roland", "Korg", "Yamaha", "Waldorf", "Kawai", "E-mu", "Akai", 
    "Ensoniq", "Oberheim", "Casio", "Alesis", "Sequential", "Moog", 
    "Nord", "Arturia", "Novation", "Elektron", "Access",
    "Quasimidi", "Kurzweil", "Hohner", "Crumar", "Vermona", "Simmons"
]
```
- **Total brands**: 24.
- **Position of "Simmons"**: Index 23 (position 24 of 24) — **it is the VERY LAST item in `TARGET_BRANDS`**.
- There are no subsequent brands defined in `TARGET_BRANDS`.

#### 1.3 Task Queue Construction in `scrape_all_platforms()`
In `synth_arbitrage/scraper.py:297-310`:
```python
kleinanzeigen_tasks = [
    scrape_kleinanzeigen_brand(brand, browser, major_brands, seen_links, stealth_async, semaphore)
    for brand in TARGET_BRANDS
]

ebay_tasks = [
    scrape_ebay_brand(brand, browser, seen_links, semaphore)
    for brand in TARGET_BRANDS
]

thomann_task = [scrape_thomann_bstock(browser, stealth_async)]

all_tasks = kleinanzeigen_tasks + ebay_tasks + thomann_task
results_lists = await asyncio.gather(*all_tasks, return_exceptions=True)
```
- `kleinanzeigen_tasks` produces 24 coroutines (`Roland` through `Simmons`).
- `ebay_tasks` produces 24 coroutines (`Roland` through `Simmons`).
- `thomann_task` produces 1 coroutine.
- Total tasks: **49 coroutines** passed simultaneously to `asyncio.gather(*all_tasks, return_exceptions=True)`.

Because `kleinanzeigen_tasks` are created first in `all_tasks` list concatenation, tasks are queued in exact list order:
1. `scrape_kleinanzeigen_brand("Roland", ...)` (Task 1)
2. ...
3. `scrape_kleinanzeigen_brand("Simmons", ...)` (Task 24)
4. `scrape_ebay_brand("Roland", ...)` (Task 25)
5. ...
6. `scrape_ebay_brand("Simmons", ...)` (Task 48)
7. `scrape_thomann_bstock(...)` (Task 49)

Since "Simmons" is at the end of both `kleinanzeigen_tasks` and `ebay_tasks`, "Simmons" coroutines acquire the semaphore and finish scraping **last**. Thus, when logging shows "Simmons" completing, all scraping tasks in `asyncio.gather()` have finished or failed, and the process transitions to the cleanup phase (`browser.close()` and context manager exit).

---

### Question 2: Playwright Initialization, Context & Page Lifecycle, and Resource Leaks

#### 2.1 Object Creation Architecture
- **Browser Instance**: Single Chromium browser launched asynchronously in `scrape_all_platforms()` (`scraper.py:290`):
  ```python
  browser = await p.chromium.launch(headless=True)
  ```
  This single `browser` object is shared by reference across all 49 worker coroutines.

- **Browser Contexts**: Created per task:
  - `scrape_kleinanzeigen_brand` (`scraper.py:45`): `context = await browser.new_context(...)`
  - `scrape_ebay_brand` (`scraper.py:148`): `context = await browser.new_context(...)`
  - `scrape_thomann_bstock` (`scraper.py:200`): `context = await browser.new_context(...)`
  Total browser contexts created during execution: **49 contexts**.

- **Pages**: Created per context:
  - `scrape_kleinanzeigen_brand` (`scraper.py:46`): `page = await context.new_page()`
  - `scrape_ebay_brand` (`scraper.py:149`): `page = await context.new_page()`
  - `scrape_thomann_bstock` (`scraper.py:201`): `page = await context.new_page()`

#### 2.2 Resource Leak Analysis
1. **Explicit `page.close()` Missing**: `page.close()` is never called in any scraper handler.
2. **Context Leak in `scrape_kleinanzeigen_brand`**:
   In `scrape_kleinanzeigen_brand` (`scraper.py:43-124`), lines 45-46 allocate `context` and `page`. The context cleanup call at line 122 (`await context.close()`) is **NOT** inside a `finally` block:
   ```python
   # synth_arbitrage/scraper.py:43-124
   async with semaphore:
       logging.info(f"--- Iniciando escaneo de marca: {brand} (Kleinanzeigen) ---")
       context = await browser.new_context(...)
       page = await context.new_page()

       if stealth_async:
           await stealth_async(page)
       ...
       # Inner query loops...
       ...
       await context.close()  # Line 122 - UNPROTECTED!
       await asyncio.sleep(random.uniform(4.0, 8.0))
   ```
   If an exception occurs during `stealth_async(page)` injection, URL construction, or outside the inner `try...except` blocks during page processing, control escapes line 122. **`await context.close()` is never called, leaking the context and page in the browser.**
3. Contrast with `scrape_ebay_brand` (`scraper.py:177-178`) and `scrape_thomann_bstock` (`scraper.py:266-267`), which correctly use `try ... finally: await context.close()`.

---

### Question 3: Mechanism of the Freeze / Hang After "Simmons"

The freeze after "Simmons" is caused by a combination of four contributing mechanisms:

#### Factor 1: Playwright Event Loop & Driver Transport Hang on Shut Down
- `scrape_all_platforms()` uses `async with async_playwright() as p:` (`scraper.py:289`).
- Inside the `try...finally` block, it calls `await browser.close()` at line 321:
  ```python
  finally:
      await browser.close()
  ```
- When `async with async_playwright() as p:` exits (line 322), the context manager calls `p.stop()`, which sends a `close` JSON RPC request over stdin to the Playwright driver process (`playwright.cmd` / Node.js driver) and waits for the asyncio transport task (`Connection.run()`) to terminate.
- If browser contexts or pages were leaked (due to the unprotected `context.close()` in `scrape_kleinanzeigen_brand`), or if background CDP listeners registered by `playwright_stealth` (`Page.addScriptToEvaluateOnNewDocument`) remain active on unclosed targets, Chromium process handles or driver pipe readers remain open.
- The Python asyncio transport `_read_ready` or pipe reader task never receives EOF, causing `asyncio.run(main())` in `diagnostic.py:17` to hang indefinitely at shutdown waiting for background event loop tasks to finalize.

#### Factor 2: Semaphore Contention & Idle Sleep Holding Lock
- In `scraper.py:295`, `semaphore = asyncio.Semaphore(2)` is instantiated and passed to all 24 Kleinanzeigen tasks AND all 24 eBay tasks (48 tasks total).
- Look at where `asyncio.sleep` is located in `scrape_kleinanzeigen_brand`:
  ```python
  # synth_arbitrage/scraper.py:122-123
  await context.close()
  await asyncio.sleep(random.uniform(4.0, 8.0)) # INSIDE async with semaphore!
  ```
  And in `scrape_ebay_brand`:
  ```python
  # synth_arbitrage/scraper.py:178-179
  finally:
      await context.close()
      await asyncio.sleep(random.uniform(2.0, 5.0)) # INSIDE async with semaphore!
  ```
- Because `await asyncio.sleep` is inside `async with semaphore:`, every task holds one of the two available semaphore slots while sitting completely idle for 4-8 seconds (Kleinanzeigen) or 2-5 seconds (eBay).
- This bottleneck severely throttles task throughput: with 48 tasks sharing 2 slots, idle sleeping alone adds over **110 seconds** of lock delay. Tasks queued near the end of the list ("Simmons") are delayed significantly before they even begin.

#### Factor 3: Excessive Cumulative Time per Brand & Rate Limiting / IP Blocks
- `scrape_kleinanzeigen_brand` iterates over up to 8 search queries per brand (`brand-synthesizer`, `brand-synth`, `brand-drum-machine`, etc.).
- For each query, it attempts up to 2 page numbers.
- For each page attempt, it runs up to 3 retries with `timeout=20000` (20s) and random sleeps:
  - `await asyncio.sleep(random.uniform(2.5, 5.5))` before goto
  - `await page.goto(url, wait_until="domcontentloaded", timeout=20000)`
  - `await asyncio.sleep(random.uniform(3.0, 6.0))` after goto
  - `await asyncio.sleep(random.uniform(5.0, 10.0))` between retries
- A failing or rate-limited query on Kleinanzeigen can take over 90 seconds. With 8 queries per brand, a single brand task can take up to 10-12 minutes!
- By the time brand #24 ("Simmons") is reached, Kleinanzeigen has received nearly 180 sequential page requests from the scraper, leading to target page connection drops or hung HTTP sockets.

#### Factor 4: Total Lack of Global and Task Timeouts
- Neither `diagnostic.py` nor `scrape_all_platforms()` wraps `asyncio.gather()` in `asyncio.wait_for(...)` or `asyncio.timeout(...)`.
- Individual brand tasks have no top-level timeout wrapping their query loops.
- If a Playwright `page.goto()` hangs on network response without throwing an exception or if `asyncio.gather()` waits on a stalled coroutine, execution blocks forever without timing out.

---

## Code Base & Test Audit Findings

1. **Unit Test Failure in `tests/test_scraper.py`**:
   Running `./venv/bin/python -m pytest` revealed 1 test failure out of 140 tests:
   ```
   FAILED tests/test_scraper.py::test_scrape_ebay_brand - TypeError: scrape_ebay_brand() got an unexpected keyword argument 'page'
   ```
   **Cause**: `test_scrape_ebay_brand` passes `page=mock_playwright_page`, but `scrape_ebay_brand` signature in `synth_arbitrage/scraper.py:127` expects `(brand, browser, seen_links, semaphore)`.

---

## Recommended Action Plan for M6.2 (Implementer)

1. **Fix Resource Leaks in `scrape_kleinanzeigen_brand`**:
   - Wrap `context` and `page` creation and scraping logic in a `try ... finally` block.
   - Explicitly call `await page.close()` and `await context.close()` in `finally`.

2. **Fix Semaphore Scope**:
   - Move `await asyncio.sleep(...)` **OUTSIDE** the `async with semaphore:` block in both `scrape_kleinanzeigen_brand` and `scrape_ebay_brand` so idle sleeping does not block other tasks from acquiring the semaphore.

3. **Add Robust Timeout Management**:
   - Wrap `asyncio.gather()` in `scrape_all_platforms()` with a global timeout (e.g., `asyncio.wait_for(..., timeout=300)`).
   - Add per-brand task timeouts using `asyncio.wait_for` inside brand worker functions.

4. **Hardening Browser & Playwright Shutdown**:
   - Ensure all contexts are explicitly closed before calling `await browser.close()`.
   - Wrap Playwright context manager exit in a clean fallback.

5. **Fix Test Suite**:
   - Update `tests/test_scraper.py::test_scrape_ebay_brand` signature and arguments to match `scrape_ebay_brand(brand, browser, seen_links, semaphore)`.
