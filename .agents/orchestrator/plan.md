# Implementation Plan: Thomann B-Stock Integration

## Objective
Integrate Thomann B-Stock synthesizer deals into SynthRadar backend scraping, categorize them distinctly without second-hand margin calculation, interleave 1 B-Stock ad per 8 normal user ads in the frontend grid (`index.html`) with native ad styling, and update the automated pytest suite to 100% pass including Thomann B-Stock unit tests.

## Milestones & Work Items

### Milestone M5.1: Exploration & Architecture Analysis
- **Goal**: Analyze existing scraper routines in `synth_arbitrage/scraper.py`, analysis logic in `synth_arbitrage/analysis.py`, frontend rendering in `index.html`, and tests in `tests/`.
- **Assigned to**: `teamwork_preview_explorer` (2 parallel instances).

### Milestone M5.2: Backend & Frontend Implementation
- **Goal**:
  1. Modify `synth_arbitrage/scraper.py` to extract Thomann B-Stock listings (model, URL, price, main image URL).
  2. Update `synth_arbitrage/analysis.py` to categorize Thomann B-Stock listings (e.g. `Plataforma = "Thomann B-Stock"`), preventing second-hand margin/savings calculation.
  3. Modify `index.html` `fetchData()` and grid rendering to separate normal opportunities from B-Stock ads and interleave 1 B-Stock per 8 normal ads with highlighted CSS style.
  4. Update `tests/` suite to 100% passing including specific tests for Thomann B-Stock handling.
- **Assigned to**: `teamwork_preview_worker`.

### Milestone M5.3: Verification, Adversarial Testing & Forensic Audit
- **Goal**:
  1. Review implementation for robustness, syntax, interface conformance.
  2. Challenge grid interleaving math, margin logic safety, and scraper resilience.
  3. Perform Forensic Integrity Audit to verify clean implementation (no hardcoding, cheating, or facades).
- **Assigned to**: `teamwork_preview_reviewer`, `teamwork_preview_challenger`, `teamwork_preview_auditor`.

## Acceptance Criteria
- [ ] Pytest suite passes 100%, including a test verifying Thomann B-Stock item tagging and margin calculation safety.
- [ ] Backend script connects to Thomann B-Stock and extracts items clean without errors.
- [ ] `index.html` separates normal vs B-Stock items and interleaves 1 B-Stock card per 8 normal cards (at positions 8, 16, 24...).
- [ ] B-Stock cards have distinct native ad visual CSS styling.
- [ ] Forensic Auditor verdict is CLEAN.
