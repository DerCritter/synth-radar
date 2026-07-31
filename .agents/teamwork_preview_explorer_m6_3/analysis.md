# Comprehensive Async Concurrency & Deadlock Analysis Report

## Executive Summary

This report delivers a forensic architectural analysis of the async concurrency model and execution behavior of `diagnostic.py` and `synth_arbitrage/scraper.py` in SynthRadar. The investigation identified the root causes behind the reported scraper "freeze/hang after brand Simmons", Playwright resource management vulnerabilities, semaphore queueing bottlenecks, and anti-bot/logging gaps.

---

## 1. Async Concurrency Model & Task Execution Breakdown

### 1.1 Task Instantiation & `asyncio.gather` Structure
In `synth_arbitrage/scraper.py` (`scrape_all_platforms()`), async tasks are instantiated as coroutine list comprehensions for each brand in `TARGET_BRANDS`:

```python
kleinanzeigen_tasks = [scrape_kleinanzeigen_brand(...) for brand in TARGET_BRANDS]
ebay_tasks = [scrape_ebay_brand(...) for brand in TARGET_BRANDS]
thomann_task = [scrape_thomann_bstock(browser, stealth_async)]

all_tasks = kleinanzeigen_tasks + ebay_tasks + thomann_task
results_lists = await asyncio.gather(*all_tasks, return_exceptions=True)
```

- **Total Coroutines**: 24 Kleinanzeigen tasks + 24 eBay tasks + 1 Thomann task = **49 concurrent coroutines** passed to `asyncio.gather`.
- **Execution Order**: `asyncio.gather` schedules coroutines in array order.

### 1.2 Semaphore Bottlenecks & Platform Serialization
- A single `semaphore = asyncio.Semaphore(2)` is shared between `scrape_kleinanzeigen_brand` and `scrape_ebay_brand`.
- Because `all_tasks` places all 24 Kleinanzeigen tasks ahead of eBay tasks, the first two Kleinanzeigen tasks (`Roland` and `Korg`) acquire both available semaphore tokens immediately.
- **Platform Serialization Flaw**: All 24 eBay tasks and all remaining 22 Kleinanzeigen tasks are forced to wait in the semaphore queue. eBay scraping cannot begin a single task until all 24 Kleinanzeigen tasks have finished.
- **Sleep inside Semaphore Lock**: Both Kleinanzeigen (line 123) and eBay (line 179) perform cooldown sleeps (`asyncio.sleep(4..8)` and `asyncio.sleep(2..5)`) *inside* the `async with semaphore:` context, holding active concurrency slots idle for several seconds per brand.

---

## 2. Playwright Resource Lifecycle & Concurrency Vulnerabilities

### 2.1 Browser vs Context Isolation
- A single Playwright `Browser` instance is launched at the top level (`browser = await p.chromium.launch(headless=True)`).
- Playwright's `async_api` supports sharing a `Browser` instance across coroutines on the same event loop, provided each coroutine creates its own `BrowserContext` and `Page`.

### 2.2 Unhandled Exception Resource Leaks
1. **`scrape_kleinanzeigen_brand` (Lines 45-122)**:
   ```python
   context = await browser.new_context(viewport={"width": 1280, "height": 800}, locale="de-DE")
   page = await context.new_page()
   ...
   await context.close()  # Line 122 - OUTSIDE try/finally!
   ```
   If any exception occurs during `stealth_async(page)`, navigation, DOM processing, or sleep calls, `await context.close()` is never executed. This leaks Chromium browser contexts, renderer sub-processes, and websocket connection handles.

2. **`scrape_ebay_brand` & `scrape_thomann_bstock` Unbound Variable Defect**:
   ```python
   try:
       context = await browser.new_context(...)
       ...
   finally:
       await context.close()
   ```
   If `browser.new_context()` raises an exception, `finally:` executes `await context.close()`, causing an `UnboundLocalError: local variable 'context' referenced before assignment` that masks the original exception.

### 2.3 Stealth Gaps on eBay
- `scrape_ebay_brand` does NOT take or execute `stealth_async`. Headless Chromium connections to eBay DE trigger bot detection blocks, CAPTCHA responses, or network request hangs.

---

## 3. Empirical Diagnostics & Root Cause of the "Simmons Freeze"

### 3.1 Live Execution Log Trace
Execution of `python3 diagnostic.py` revealed the following timeline:
- **T+0s**: Thomann B-Stock and Kleinanzeigen `Roland` + `Korg` start.
- **T+11.5s**: Thomann B-Stock completes (returning 96 listings).
- **T+12s - T+70s**: `Roland` and `Korg` execute query 1 (`-synthesizer` p1/p2), query 2 (`-synth`), query 3 (`-drum-machine`), query 4 (`-groovebox`), etc. Each query request takes 10–15 seconds due to delay sleeps (`2.5–5.5s` pre-load, `3.0–6.0s` post-load, `1.0–2.5s` mouse/wheel).
- **Total Kleinanzeigen Duration**: 24 brands * 8 queries = ~180 HTTP requests. At ~13s per request across 2 semaphore slots, Kleinanzeigen takes **~20 to 30 minutes** to finish.

### 3.2 The Root Cause of the "Simmons Freeze"
- "Simmons" is brand #24 (the final brand in `TARGET_BRANDS`).
- `scrape_kleinanzeigen_brand` logs every brand start (`--- Iniciando escaneo de marca: Simmons (Kleinanzeigen) ---`) and query result (`[Simmons Synth p1] Encontrados 0 anuncios.`).
- When "Simmons" completes, Kleinanzeigen scraping is finished, and `ebay_tasks` acquire the semaphore.
- **CRITICAL LOGGING DEFECT**: `scrape_ebay_brand` contains **ZERO `logging.info()` statements**. Lines 127–180 of `synth_arbitrage/scraper.py` only contain error logging (`logging.error(...)`).
- **Conclusion**: Right after brand "Simmons" finishes, console output completely stops. The application is NOT deadlocked; it is executing eBay scraping in total logging blackout. Furthermore, if eBay blocks the un-stealthed headless browser, Playwright network calls stall without visual feedback.

---

## 4. Required Architectural Remediation

To eliminate hangs, deadlocks, logging blackouts, and platform serialization, the following changes are required:

| # | Remediation | Rationale / Implementation |
|---|---|---|
| 1 | **Separate Per-Platform Semaphores** | Implement `kleinanzeigen_semaphore = asyncio.Semaphore(2)` and `ebay_semaphore = asyncio.Semaphore(2)`. Allows Kleinanzeigen and eBay to scrape concurrently in parallel. |
| 2 | **Robust `try...finally` Context Management** | Initialize `context = None` before `try:` block; close `context` safely in `finally:` if `context is not None`. Prevents resource leaks and `UnboundLocalError`. |
| 3 | **Comprehensive Progress Logging for eBay** | Add `logging.info(f"--- Iniciando escaneo de marca: {brand} (eBay) ---")` and result logging inside `scrape_ebay_brand`. Eliminates logging blackout after "Simmons". |
| 4 | **Apply Playwright Stealth to eBay** | Pass `stealth_async` to `scrape_ebay_brand` and call `await stealth_async(page)` on new pages to evade eBay anti-bot blocks. |
| 5 | **Move Cooldown Sleep Outside Semaphore** | Move `await asyncio.sleep(...)` outside `async with semaphore:` so waiting tasks immediately gain access to the semaphore token. |
| 6 | **Enforce Task & Request Timeouts** | Wrap `page.goto` and brand task calls in `asyncio.wait_for(..., timeout=...)` to guard against stalled TCP connections or headless browser freezes. |
| 7 | **Query Burden Optimization** | Streamline Kleinanzeigen query lists per brand or make them configurable to reduce unnecessary HTTP load and sleep accumulation. |
