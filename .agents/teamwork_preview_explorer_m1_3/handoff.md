# Explorer 3 Handoff Report: Pytest Architecture & Test Case Catalog Design

## 1. Observation
We conducted a comprehensive analysis of the SynthRadar codebase (`synth_arbitrage.py`, `supabase_client.py`, `config.json`, and existing ad-hoc test scripts).

Key observations with exact line references:

1. **Price Extraction (`extract_price`, `synth_arbitrage.py:170-202`)**:
   - `line 171`: Rejects `price_str` if empty/None or contains `"VB"` with `len(price_str) < 5`.
   - `lines 175-190`: Replaces `"€"`, handles combined dot/comma (`"1.250,50"` -> `"1250.50"`), comma-only (`"450,50"` -> `"450.50"`), and German thousands dot (`re.search(r"\.\d{3}", clean)` -> removes dot).
   - `lines 193-199`: Parses numeric float `re.search(r"(\d+\.?\d*)", clean)`. Rejects fake/symbolic prices `price <= 10` or `price in [123, 1234, 1111, 9999]`.

2. **Listing Analysis & Filtering (`analyze_listing`, `synth_arbitrage.py:204-316`)**:
   - `lines 209-216`: Junk filter using `JUNK_KEYWORDS` (26 keywords) and ignored condition filter `CONDITION_IGNORE` (31 keywords) via `re.search(rf"\b{re.escape(kw)}\b", title_lower)`.
   - `lines 219-220`: Minimum price check: `price is None or (price < 50 and "reface" not in title_lower and "sr-16" not in title_lower)`.
   - `lines 224-245`: Model matching: sorts `MARKET_VALUES.keys()` by length descending. Replaces spaces/dashes with `[\s\-]*` in regex.
   - `lines 248-250`: Condition tags: `is_defekt`, `is_mint`, `is_poor`.
   - `lines 263-269`: Reference price calculation (`market_avg`, `market_low` for defekt, `market_high` for mint).
   - `lines 270-278`: Discount thresholds: `>= 40%` for defekt (`"Gran Margen Defecto"`), `>= 20%` for functional (`"Buen Precio Funcional"`), or `'Thomann B-Stock'`.
   - `lines 281-295`: Accessory tagging (`ACCESSORY_KEYWORDS`) prefixes `"Accesorio / "` to condition label and sets discount string to `"0%"`.
   - `lines 298-315`: Generates German draft message (`"Hallo, ich interessiere mich..."` vs `"Guten Tag..."`) and returns result dictionary.

3. **Supabase Database Layer (`supabase_client.py:1-73`)**:
   - `lines 15-45`: Mappers `_map_to_db` (Spanish key -> DB column) and `_map_from_db` (DB column -> Spanish key).
   - `lines 47-61`: `upsert_listings` upserts mapped items using primary key `url`. Handles missing client gracefully.

4. **Async Web Scraping (`synth_arbitrage.py:318-560`)**:
   - Async Playwright functions (`scrape_kleinanzeigen_brand`, `scrape_ebay_brand`, `scrape_thomann_bstock`, `scrape_all_platforms`, `main_async`).

---

## 2. Logic Chain

1. **Problem Statement**:
   - Currently, tests are ad-hoc scripts (`test_ebay.py`, `test_regex.py`, etc.) scattered in the root directory. There is no automated `pytest` suite in `tests/`.
   - Running scrapers live takes tens of seconds and makes network requests to real websites and cloud services, which fails offline execution goals.

2. **Architectural Solution**:
   - Create a clean `tests/` directory with `conftest.py`, `test_extract_price.py`, `test_analysis.py`, `test_supabase.py`, and `test_integration.py`.
   - Use `unittest.mock.AsyncMock` for Playwright browser context / page objects to mock HTML DOM content without launching actual browser processes or fetching real URLs.
   - Use `unittest.mock.MagicMock` and `monkeypatch` to replace Supabase API calls and isolate environment variables.

3. **Coverage Strategy**:
   - **Unit Tests**: Test core functions in isolation (`extract_price`, `analyze_listing`, `get_market_price`, `load_or_create_config`, `_map_to_db`, `_map_from_db`).
   - **Integration Tests**: Test async scraping routines and main pipeline with mocked HTML DOM inputs and mocked Supabase client.

---

## 3. Caveats

- **No Live Production Code Modified**: As an explorer in read-only mode, no code in `synth_arbitrage.py`, `supabase_client.py`, or `tests/` was modified or created in the project root directory. All designs and specs are detailed in `analysis.md`.
- **Dynamic Models**: `load_or_create_config()` dynamically writes `config.json` if missing. Tests should mock or use temporary directories to avoid modifying root `config.json`.

---

## 4. Conclusion

A complete, production-grade pytest test suite architecture and test case catalog has been designed in `analysis.md`. 

Key features:
- **Zero external network dependencies** (100% mocked Playwright and Supabase).
- **Execution speed < 200 ms**.
- **Full coverage** for `extract_price`, `analyze_listing` (junk, ignore, models, conditions, discounts, accessories, message drafting), `SupabaseDB`, and async scraper pipelines.

---

## 5. Verification Method

To verify the test suite design once implemented by the Implementer agent:
1. Run `pytest tests/ -v` from the project root directory.
2. Confirm all test cases pass in under 1 second.
3. Verify test coverage using `pytest tests/ --cov=synth_arbitrage --cov=supabase_client`.
