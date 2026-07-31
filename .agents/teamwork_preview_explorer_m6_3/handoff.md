# Explorer 3 Handoff Report — Milestone 6.1

## 1. Observation

### Codebase Observations
1. **Task Scheduling & Concurrency Ordering** (`synth_arbitrage/scraper.py:295-310`):
   - `semaphore = asyncio.Semaphore(2)` is instantiated at line 295.
   - `kleinanzeigen_tasks` (24 coroutines for `TARGET_BRANDS`) are created at lines 297-300.
   - `ebay_tasks` (24 coroutines for `TARGET_BRANDS`) are created at lines 302-305.
   - `thomann_task` (1 coroutine) is created at line 307.
   - `all_tasks = kleinanzeigen_tasks + ebay_tasks + thomann_task` (line 309).
   - `results_lists = await asyncio.gather(*all_tasks, return_exceptions=True)` (line 310).

2. **Semaphore Contention & Sleeping Lock** (`synth_arbitrage/scraper.py:43-124, 146-180`):
   - `scrape_kleinanzeigen_brand` acquires `async with semaphore:` at line 43.
   - Line 123 in `scrape_kleinanzeigen_brand`: `await asyncio.sleep(random.uniform(4.0, 8.0))` is inside the `async with semaphore:` block.
   - `scrape_ebay_brand` acquires `async with semaphore:` at line 146.
   - Line 179 in `scrape_ebay_brand`: `await asyncio.sleep(random.uniform(2.0, 5.0))` is inside the `async with semaphore:` block.

3. **Logging Disparity** (`synth_arbitrage/scraper.py:44, 91, 127-180`):
   - `scrape_kleinanzeigen_brand` logs startup at line 44 (`logging.info(f"--- Iniciando escaneo de marca: {brand} (Kleinanzeigen) ---")`) and page results at line 91 (`logging.info(f"[{search_display} p{page_num}] Encontrados {len(ads)} anuncios.")`).
   - `scrape_ebay_brand` (lines 127-180) contains NO `logging.info(...)` calls. The only log is error handling at line 176 (`logging.error(...)`).

4. **Resource Management & Exception Vulnerability** (`synth_arbitrage/scraper.py:45-122, 147-178, 199-267`):
   - `scrape_kleinanzeigen_brand`: `context = await browser.new_context(...)` (line 45), `page = await context.new_page()` (line 46). Line 122 `await context.close()` is placed outside any `try...finally` block.
   - `scrape_ebay_brand` (line 147) and `scrape_thomann_bstock` (line 199): `try: context = await browser.new_context(...)` assigns `context` inside `try`. `finally: await context.close()` raises `UnboundLocalError` if `new_context()` throws.
   - `scrape_ebay_brand` does NOT pass or invoke `stealth_async(page)`.

### Live Execution Log Observation (`python3 diagnostic.py`)
Execution task `task-19` log output:
```text
2026-07-30 13:30:20,098 - INFO - Iniciando escaneo en kleinanzeigen.de y ebay.de con Playwright (STEALTH MODE)...
2026-07-30 13:30:20,497 - INFO - --- Iniciando escaneo de marca: Roland (Kleinanzeigen) ---
2026-07-30 13:30:20,499 - INFO - --- Iniciando escaneo de marca: Korg (Kleinanzeigen) ---
2026-07-30 13:30:20,500 - INFO - Iniciando escaneo de Thomann B-Stock (Stealth)...
2026-07-30 13:30:32,015 - INFO - [Thomann B-Stock] Encontrados 96 anuncios.
2026-07-30 13:30:32,236 - INFO - [Roland Synthesizer p1] Encontrados 25 anuncios.
2026-07-30 13:30:32,662 - INFO - [Korg Synthesizer p1] Encontrados 25 anuncios.
...
2026-07-30 13:31:27,051 - INFO - [Korg Sampler p1] Encontrados 0 anuncios.
2026-07-30 13:31:31,460 - INFO - [Roland Sampler p1] Encontrados 0 anuncios.
```

---

## 2. Logic Chain

1. **Premise 1**: `asyncio.gather(*all_tasks)` executes coroutines in array order (`kleinanzeigen_tasks` first, `ebay_tasks` second).
2. **Premise 2**: `semaphore = asyncio.Semaphore(2)` limits concurrent execution across all tasks that acquire it.
3. **Reasoning Step 1**: The first two Kleinanzeigen tasks (`Roland` and `Korg`) acquire both semaphore slots immediately. All remaining 22 Kleinanzeigen tasks and all 24 eBay tasks wait in line.
4. **Reasoning Step 2**: Each Kleinanzeigen brand executes 7-8 sequential search queries. Each query includes `asyncio.sleep(2.5..5.5)`, `page.goto` (up to 20s timeout), `asyncio.sleep(3.0..6.0)`, and mouse movement delays (~1-2.5s). Thus, each brand takes ~2 minutes to finish.
5. **Reasoning Step 3**: Running 24 Kleinanzeigen brands 2 at a time requires ~20 to 30 minutes. During this entire window, zero eBay tasks can start because all semaphore slots are held by Kleinanzeigen tasks.
6. **Reasoning Step 4**: "Simmons" is the 24th (and final) brand in `TARGET_BRANDS`. When brand "Simmons" finishes on Kleinanzeigen, all Kleinanzeigen tasks complete, freeing the semaphore for `ebay_tasks`.
7. **Reasoning Step 5**: `scrape_ebay_brand` has NO `logging.info(...)` statements. When eBay scraping starts after "Simmons", no log messages are emitted to stdout/stderr.
8. **Conclusion Step**: To an external observer watching console logs, execution completely stops after "Simmons", creating the false perception of an application freeze/hang. In reality, eBay scraping is executing silently without logs, or stalling due to un-stealthed headless browser anti-bot blocks on eBay DE.

---

## 3. Caveats

- **External Network Rate-Limiting**: Actual response times and anti-bot challenges on Kleinanzeigen and eBay DE depend on IP address reputation, Cloudflare Turnstile triggers, and ISP routing.
- **System Resource Usage**: Running Chromium with multiple context creations without explicit `try...finally` cleanup can accumulate memory pressure on low-RAM test environments during long scraping sessions.

---

## 4. Conclusion

The apparent scraper deadlock after brand "Simmons" is caused by a combination of:
1. **Platform Serialization**: All 24 Kleinanzeigen tasks precede eBay tasks in `asyncio.gather`, locking the shared `Semaphore(2)` for 20-30 minutes.
2. **Logging Blackout**: `scrape_ebay_brand` has zero startup or progress logging. When Kleinanzeigen finishes at brand "Simmons", log output stops completely while eBay scraping runs silently.
3. **Anti-Bot Susceptibility**: eBay tasks lack `stealth_async` protection, causing headless Chromium requests to be blocked or hung by eBay DE anti-bot systems.
4. **Resource Leak Risks**: `scrape_kleinanzeigen_brand` lacks `try...finally` around `context.close()`, while `scrape_ebay_brand` risks `UnboundLocalError` if `new_context()` fails.

---

## 5. Verification Method

### How to Verify Findings Independently:
1. **Inspect Source Files**:
   - View `synth_arbitrage/scraper.py` lines 43-124, 146-180, and 295-310 to confirm task list order, semaphore sharing, sleep locations, and absence of `logging.info` in `scrape_ebay_brand`.
   - View `synth_arbitrage/config.py` line 55 to confirm "Simmons" is the 24th/last element in `TARGET_BRANDS`.
2. **Run Diagnostic Log Check**:
   - Run `python3 diagnostic.py`.
   - Observe that Thomann finishes in ~11s, Roland/Korg start immediately, and progress logs are printed per query.
   - Note the timestamp intervals (~13s per query, ~2 mins per brand) proving 20+ minute total Kleinanzeigen runtime before eBay can run.
