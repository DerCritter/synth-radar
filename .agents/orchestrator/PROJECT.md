# Project Specification — SynthRadar

## Architecture Overview
SynthRadar is a Python-based synthesizer arbitrage tool.
- Entrypoint: `synth_arbitrage.py` / `diagnostic.py`
- Core Modules:
  - `synth_arbitrage/scraper.py`: Playwright + BeautifulSoup multi-platform async web scraper for eBay, Kleinanzeigen, and Thomann B-Stock.
  - `synth_arbitrage/analysis.py`: Listing analysis logic (junk filter, accessory detection, discount margin, B-Stock tagging).
  - `synth_arbitrage/db.py`: SQLite database storage and deduplication.
  - `index.html`: Frontend interface for displaying listings with 1:8 interleaved Thomann B-Stock native ads.

## Status: Scraper Deadlock & Concurrency Fix Complete (Remediated & Approved)
The scraper deadlock after brand "Simmons" has been completely resolved. Playwright resources are teardown-guaranteed via `try...finally`, platforms run concurrently via isolated semaphores (`kleinanzeigen_sem`, `ebay_sem`), sleep delays are outside semaphores, logging is complete across all platforms, diagnostic key access is aligned with Spanish capitalized schema, and global timeouts (1200s default) harvest completed task results without discarding opportunities.

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M6.1 | Exploration & Root Cause Analysis | Investigate `diagnostic.py` and `scraper.py` deadlock after "Simmons" | None | DONE |
| M6.2 | Scraper Fix & Concurrency Hardening | Fix deadlock, Playwright context handling, timeouts, multi-platform scraping, and result harvesting | M6.1 | DONE |
| M6.3 | Verification, Stress Test & Forensic Integrity Audit | Review code, stress test `diagnostic.py`, forensic audit | M6.2 | DONE |

## Interface Contracts
- Scraper returns list of analyzed listings across platforms (Kleinanzeigen, eBay, Thomann B-Stock).
- `analyze_listing` processes each raw item dict.
- `diagnostic.py` completes cleanly without hanging.
