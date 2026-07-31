# Task Plan — Scraper Freeze & Deadlock Fix (SynthRadar)

## Objective
Identify and resolve why the Python web scraper (Playwright + BeautifulSoup) freezes after processing brand "Simmons". Ensure async Playwright tasks for eBay, Kleinanzeigen, and Thomann B-Stock run concurrently without blocking/deadlocking or exhausting browser contexts, with robust error handling and logging, so `python3 diagnostic.py` completes fully and reliably.

## Requirements Checklist
- [ ] R1: Identify and fix scraper deadlocks (resolve why freeze occurs after "Simmons", ensure async Playwright tasks run concurrently without blocking/exhaustion).
- [ ] R2: Reliable multi-platform scraping (extract data from Kleinanzeigen, eBay, Thomann B-Stock and process via `analyze_listing`).
- [ ] R3: Error handling and logging (robust try/except blocks and timeouts around navigation and parsing).

## Acceptance Criteria
- [ ] `python3 diagnostic.py` completes fully without hanging indefinitely.
- [ ] Logs show successful scraping attempts for Kleinanzeigen, eBay, and Thomann B-Stock.
- [ ] No syntax errors or Playwright concurrency exceptions during a full run.

## Milestone Breakdown

### Milestone 6.1: Code Exploration & Root Cause Analysis
- **Goal**: Analyze `diagnostic.py`, `synth_arbitrage/scraper.py`, Playwright context/browser lifecycle, brand list iteration, platform handlers, and concurrency mechanisms to pinpoint exact deadlock / freeze mechanism after "Simmons".
- **Workers**: 3 Explorers (`teamwork_preview_explorer`)
  - Explorer 1: Inspect `diagnostic.py`, brand list processing ("Simmons"), Playwright context and page allocation, lifecycle management.
  - Explorer 2: Inspect platform scraping code (eBay, Kleinanzeigen, Thomann B-Stock), BeautifulSoup parsing, error handling, timeouts.
  - Explorer 3: Run diagnostic/debug inspection, inspect async task scheduling (`asyncio.gather`, semaphores, context leaks, socket/page hanging).

### Milestone 6.2: Scraper Fix & Concurrency Hardening
- **Goal**: Implement fix for deadlock/freeze, robust Playwright context management, per-platform timeouts, brand iteration isolation, error logging.
- **Workers**: 1 Worker (`teamwork_preview_worker`)
- **Verification**: Run `python3 diagnostic.py` and unit test suite.

### Milestone 6.3: Multi-Agent Review, Challenger Stress Testing & Forensic Integrity Audit
- **Goal**: Rigorous multi-agent validation.
- **Workers**: 2 Reviewers, 2 Challengers, 1 Forensic Auditor (`teamwork_preview_auditor`).
- **Gate Criteria**:
  1. `python3 diagnostic.py` completes cleanly with all platforms logged.
  2. 2 Reviewer PASS verdicts.
  3. 2 Challenger PASS verdicts under stress/concurrency testing.
  4. Forensic Auditor verdict is CLEAN (no hardcoded diagnostic outputs, no skipped scraping platforms, no integrity violations).
