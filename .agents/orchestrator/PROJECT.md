# Project: SynthRadar Backend Refactoring and Thomann B-Stock Integration

## Architecture
- `synth_arbitrage.py`: Main entry point script preserving original CLI/execution interface.
- Core Business Logic & Analysis: Extracted to dedicated analysis module (`synth_arbitrage/analysis.py`: `analyze_listing`, price parsing, discount calculation, Thomann B-Stock platform tagging and margin safety).
- Web Scraping Infrastructure: Playwright/Requests-based scraping in `synth_arbitrage/scraper.py` for Kleinanzeigen, eBay, Thomann B-Stock.
- Database Layer: Supabase client & DB ops isolated in `supabase_client.py` and `synth_arbitrage/db.py`.
- Frontend Grid & Interleaving: `index.html` fetches data, separates normal user ads and Thomann B-Stock ads, and interleaves 1 B-Stock ad every 8 user ads (positions 8, 16, 24...) with native ad CSS styling.
- Unit Test Suite: Pytest-based tests in `tests/` directory with zero network/DB dependencies, including Thomann B-Stock tests.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Architecture Exploration | Deep codebase investigation and blueprint | None | DONE |
| M2 | Modular Refactoring | Separate scraper, logic, DB + type hints & docstrings | M1 | DONE |
| M3 | Unit Test Suite | Comprehensive pytest suite with mocks | M2 | DONE |
| M4 | Forensic Audit & Quality Verification | Reviewer + Challenger + Forensic integrity audit | M3 | DONE |
| M5 | Thomann B-Stock Integration | Scraper update, analysis categorization, index.html interleaving, updated pytest suite | M4 | IN_PROGRESS |

## Code Layout
```
.
├── ORIGINAL_REQUEST.md
├── synth_arbitrage.py        # Main entry point (calls refactored modules)
├── supabase_client.py        # Database operations client
├── index.html                # Frontend web application (fetchData & grid rendering)
├── style.css                 # Frontend styles (including B-Stock native ad styling)
├── synth_arbitrage/          # Refactored module package
│   ├── __init__.py
│   ├── config.py             # Constants (JUNK_KEYWORDS, MARKET_VALUES, etc.)
│   ├── analysis.py           # Core business logic & analyze_listing
│   ├── scraper.py            # Playwright/requests scraping routines (including Thomann)
│   └── db.py                 # DB helper routines
├── tests/
│   ├── __init__.py
│   ├── test_analysis.py      # Pytest suite for analyze_listing & Thomann B-Stock
│   ├── test_extract_price.py # Tests for price parsing logic
│   └── test_integration.py   # Entry point & mock integration tests
└── requirements.txt
```

## Interface Contracts
### `analyze_listing` Interface
- **Signature**: `analyze_listing(title: str, description: str, price: Optional[float], url: str, image_url: str = "", source: str = "Kleinanzeigen") -> Optional[Dict[str, Any]]`
- **Inputs**: raw string inputs and float price.
- **Returns**: Dictionary with keys `Modelo`, `Estado`, `Precio URL`, `Precio Mercado`, `Ahorro %`, `Plataforma`, `Enlace`, `Imagen`, `Reverb`, `Mensaje Borrador`, `last_seen` or `None` if filtered/rejected.
- **Thomann B-Stock Special Rules**: `Plataforma` set to `"Thomann B-Stock"`. `Ahorro %` set to `0.0` or `None` (no margin/savings calculation against second-hand market value).

### Frontend Interleaving Rule (`index.html`)
- Separate items into `normalItems` and `bStockItems`.
- When building `displayItems`, for every 8 `normalItems`, insert 1 `bStockItem` (position index 8, 16, 24...).
- B-Stock items receive visual styling (`b-stock-card` / native ad styling).
