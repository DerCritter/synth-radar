# SynthRadar Pytest Architecture & Test Case Catalog

## Executive Summary
This document defines the architecture, mocking strategies, test file layout, and comprehensive test case catalog for the SynthRadar test suite in `tests/`.

The primary goals of the test suite are:
1. **Zero External Dependencies & Offline Execution**: Eliminate all live HTTP requests to Kleinanzeigen, eBay, Thomann, and Supabase cloud APIs.
2. **Millisecond Execution Speed**: Execute the complete test suite in < 200 milliseconds using Python `unittest.mock` and `pytest` fixtures.
3. **100% Core Logic Coverage**: Validate price parsing (`extract_price`), filter rules, model matching, condition tagging, discount calculations, draft message generation (`analyze_listing`), and database mapping (`SupabaseDB`).

---

## 1. Pytest Architecture & File Layout

### Directory Structure
```
tests/
├── __init__.py
├── conftest.py                # Shared pytest fixtures (mock Playwright, mock Supabase, HTML fixtures)
├── test_extract_price.py      # Unit tests for price extraction logic
├── test_analysis.py           # Unit tests for listing analysis, filtering, and model matching
├── test_supabase.py           # Unit tests for SupabaseDB wrapper and object mappings
└── test_integration.py        # Mocked end-to-end scraper execution tests
```

### Module Responsibilities
- **`conftest.py`**: Provides reusable fixtures for mock Playwright pages/browsers, sample HTML fragments for Kleinanzeigen, eBay, and Thomann B-Stock, fake Supabase clients, and sample listing dictionaries.
- **`test_extract_price.py`**: Exhaustively tests `extract_price(price_str)` against all valid German price formats, edge case strings, fake prices, and malformed inputs.
- **`test_analysis.py`**: Exhaustively tests `analyze_listing(...)` against junk filtering, ignored conditions, model matching order, discount thresholds, condition tags, accessory tags, and message drafting.
- **`test_supabase.py`**: Tests `SupabaseDB` mapping routines (`_map_to_db`, `_map_from_db`), graceful handling of missing environment variables, and `upsert_listings`/`get_listings`.
- **`test_integration.py`**: Validates `scrape_kleinanzeigen_brand`, `scrape_ebay_brand`, `scrape_thomann_bstock`, and `main_async` end-to-end with mocked Playwright pages and Supabase DB calls.

---

## 2. Mocking Strategy (0 External Dependencies, Millisecond Speed)

### 2.1 Playwright Network & Browser Mocking Strategy
Playwright performs async browser automation (`async_playwright()`). In unit and integration tests, we replace network navigation with pre-recorded static HTML DOM snippets.

#### Implementation Pattern (`conftest.py`):
```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_playwright_page():
    """Provides a mocked Playwright Page object returning configurable HTML content."""
    page = AsyncMock()
    page.goto = AsyncMock(return_value=None)
    page.content = AsyncMock(return_value="<html></html>")
    page.mouse = AsyncMock()
    page.mouse.move = AsyncMock(return_value=None)
    page.mouse.wheel = AsyncMock(return_value=None)
    return page

@pytest.fixture
def mock_playwright_browser(mock_playwright_page):
    """Provides a mocked Playwright Browser object returning a mocked Context and Page."""
    context = AsyncMock()
    context.new_page = AsyncMock(return_value=mock_playwright_page)
    context.close = AsyncMock(return_value=None)
    
    browser = AsyncMock()
    browser.new_context = AsyncMock(return_value=context)
    browser.close = AsyncMock(return_value=None)
    return browser
```

### 2.2 Supabase Cloud API Mocking Strategy
`SupabaseDB` requires `SUPABASE_URL` and `SUPABASE_KEY` environment variables and connects via `supabase-py`. We mock `create_client` in `supabase_client.py` and isolate environment variables.

#### Implementation Pattern (`test_supabase.py` / `conftest.py`):
```python
@pytest.fixture
def mock_supabase_client(monkeypatch):
    """Mocks the Supabase client API calls."""
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_query = MagicMock()
    
    # Setup chainable calls: client.table("listings").upsert(...).execute()
    mock_client.table.return_value = mock_table
    mock_table.upsert.return_value = mock_query
    mock_table.select.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[{"url": "https://example.com", "modelo": "Roland MC-505"}])
    
    monkeypatch.setattr("supabase_client.create_client", lambda url, key: mock_client)
    return mock_client
```

---

## 3. Comprehensive Test Case Catalog

### Catalog Section 1: `extract_price` Unit Tests (`test_extract_price.py`)

| Test Function Name | Input `price_str` | Expected Result | Rationale & Coverage |
|-------------------|-------------------|-----------------|----------------------|
| `test_extract_price_standard_integer` | `"450 €"` | `450.0` | Standard integer price format with euro sign. |
| `test_extract_price_plain_number` | `"1200"` | `1200.0` | Plain numeric string without euro symbol. |
| `test_extract_price_german_dot_thousands` | `"1.250 €"` | `1250.0` | German thousands separator with dot followed by 3 digits. |
| `test_extract_price_german_dot_thousands_vb` | `"2.500 € VB"` | `2500.0` | Thousands dot with trailing VB negotiation flag. |
| `test_extract_price_german_comma_decimal` | `"450,50 €"` | `450.5` | German decimal format with comma. |
| `test_extract_price_dot_and_comma` | `"1.250,50 €"` | `1250.5` | Full German currency format: dot thousands + comma decimals. |
| `test_extract_price_dot_and_comma_vb` | `"2.400,00 € VB"` | `2400.0` | Full German currency format with trailing VB. |
| `test_extract_price_float_dot_decimal` | `"450.50"` | `450.5` | Standard float notation with single decimal dot (not 3 trailing digits). |
| `test_extract_price_vb_short_string` | `"VB"` / `" VB"` | `None` | Short string with length < 5 consisting only of VB. |
| `test_extract_price_symbolic_fake_prices` | `"123 €"`, `"1234 €"`, `"1111 €"`, `"9999 €"` | `None` | Fake placeholder prices used on Kleinanzeigen. |
| `test_extract_price_low_price_threshold` | `"0 €"`, `"5 €"`, `"10 €"` | `None` | Prices `<= 10 €` tagged as fake or invalid. |
| `test_extract_price_invalid_strings` | `"Zu verschenken"`, `"Anfragen"` | `None` | Non-numeric listing labels without numbers. |
| `test_extract_price_none_and_empty` | `None`, `""` | `None` | Falsey inputs handling without throwing exceptions. |

---

### Catalog Section 2: `analyze_listing` Unit Tests (`test_analysis.py`)

#### 2.1 Junk Keyword Filtering
*Rule*: Listings whose title contains any word from `JUNK_KEYWORDS` (`"case"`, `"flightcase"`, `"cover"`, `"dust"`, `"decksaver"`, `"manual"`, `"anleitung"`, `"knob"`, `"fader"`, `"pot"`, `"psu"`, `"power supply"`, `"netzteil"`, `"cable"`, `"kabel"`, `"stand"`, `"ständer"`, `"gigbag"`, `"bag"`, `"tasche"`, `"box"`, `"ovp"`, `"box only"`, `"decal"`, `"sticker"`) wrapped in `\b` word boundaries are rejected immediately.

| Test Function Name | Title | Description | Price | Expected Output |
|-------------------|-------|-------------|-------|-----------------|
| `test_junk_filter_flightcase` | `"Roland MC-505 Flightcase"` | `"Case only"` | `300.0` | `None` |
| `test_junk_filter_manual` | `"Roland Juno-106 Manual"` | `"Original manual"` | `100.0` | `None` |
| `test_junk_filter_decksaver` | `"Korg Minilogue Decksaver"` | `"Dust cover"` | `50.0` | `None` |
| `test_junk_filter_power_supply` | `"Yamaha DX7 Netzteil"` | `"PSU only"` | `50.0` | `None` |
| `test_junk_filter_word_boundary_isolation` | `"Roland MC-505 in top condition"` | `"Synth for sale"` | `350.0` | Valid Dict (does not falsely match substring) |

#### 2.2 Ignored Condition Filtering
*Rule*: Listings whose title contains any word from `CONDITION_IGNORE` (`"suche"`, `"tausche"`, `"leerkarton"`, `"manual"`, `"anleitung"`, `"flightcase"`, `"case"`, `"decksaver"`, `"dustcover"`, `"ständer"`, `"stand"`, `"pedal"`, `"kabel"`, `"tasche"`, `"bag"`, `"plugin"`, `"software"`, `"vst"`, `"clone"`, `"behringer"`, `"buch"`, `"handbuch"`, `"ramkarte"`, `"cartridge"`, `"netzteil"`, `"ersatzteil"`, `"spare"`, `"part"`, `"knöpfe"`, `"tasten"`, `"kappe"`, `"stecker"`, `"lader"`, `"anreize"`, `"ovp nur"`) are rejected immediately.

| Test Function Name | Title | Description | Price | Expected Output |
|-------------------|-------|-------------|-------|-----------------|
| `test_ignore_filter_suche` | `"Suche Roland TB-303"` | `"Looking to buy"` | `2000.0` | `None` |
| `test_ignore_filter_clone` | `"Behringer Model D (Minimoog Clone)"` | `"Analog synth"` | `200.0` | `None` |
| `test_ignore_filter_vst_software` | `"Korg Wavestation VST Plugin"` | `"Software key"` | `50.0` | `None` |

#### 2.3 Model Identification & Pattern Matching
*Rule*: Models in `MARKET_VALUES` are evaluated in order of title length (longest model name first). Pattern allows spaces, dashes, or empty gaps between model parts.

| Test Function Name | Title | Expected Model Identified | Rationale |
|-------------------|-------|---------------------------|-----------|
| `test_model_match_longest_first` | `"Korg Minilogue XD Synthesizer"` | `"Korg Minilogue XD"` | Prevents matching shorter `"Korg Minilogue"`. |
| `test_model_match_spaces_and_dashes` | `"roland mc 505 groovebox"` | `"Roland MC-505"` | Regex matches `mc 505` to `MC-505`. |
| `test_model_match_no_spaces` | `"roland mc505"` | `"Roland MC-505"` | Regex `[\s\-]*` matches `mc505` to `MC-505`. |
| `test_model_match_unknown_synth` | `"Unknown Brand Synth 3000"` | `None` | Unrecognized synth model returns `None`. |

#### 2.4 Minimum Price Threshold
*Rule*: Listings with `price < 50` return `None`, UNLESS the model title contains `"reface"` or `"sr-16"`.

| Test Function Name | Title | Price | Expected Output |
|-------------------|-------|-------|-----------------|
| `test_min_price_generic_rejected` | `"Roland MC-505"` | `45.0` | `None` (< 50) |
| `test_min_price_reface_allowed` | `"Yamaha Reface CS"` | `45.0` | Valid Dict (if discount threshold met) |
| `test_min_price_sr16_allowed` | `"Alesis SR-16"` | `40.0` | Valid Dict (if discount threshold met) |
| `test_min_price_none` | `"Roland MC-505"` | `None` | `None` |

#### 2.5 Condition Tagging, Discount Thresholds & Messaging

**Market Values Reference for Tests**:
- `"Roland MC-505"`: market range `(450, 650)` € -> `market_avg = 550` €
  - Functional (Average): `reference_price = 550` €
  - Defekt/Bastler: `reference_price = 450` € (market_low)
  - Mint: `reference_price = 650` € (market_high)

| Test Function Name | Title / Desc | Listed Price | Expected Discount % | Condition Tag | Opportunity Type | Message Draft Check |
|-------------------|--------------|--------------|---------------------|---------------|------------------|---------------------|
| `test_functional_deal_valid` | Title: `"Roland MC-505"` (price 400€) | 400.0 | `(550-400)/550 = 27.27%` (>= 20%) | `"Funcional (Average)"` | `"Buen Precio Funcional"` | Contains `"Guten Tag, ist der Roland MC-505 noch verfügbar?"` |
| `test_functional_deal_below_threshold` | Title: `"Roland MC-505"` (price 500€) | 500.0 | `(550-500)/550 = 9.09%` (< 20%) | N/A | `None` | Returns `None` |
| `test_mint_condition_deal` | Title: `"Roland MC-505 mint wie neu"` (price 500€) | 500.0 | `(650-500)/650 = 23.07%` (>= 20%) | `"Funcional (Mint)"` | `"Buen Precio Funcional"` | Evaluated against `market_high` (650€) |
| `test_defekt_deal_valid` | Title: `"Roland MC-505 defekt bastler"` (price 250€) | 250.0 | `(450-250)/450 = 44.44%` (>= 40%) | `"Defekt/Bastler"` | `"Gran Margen Defecto"` | Message contains `"würde 212€ inkl. Versand anbieten"` (`250 * 0.85`) |
| `test_defekt_deal_below_threshold` | Title: `"Roland MC-505 defekt bastler"` (price 300€) | 300.0 | `(450-300)/450 = 33.33%` (< 40%) | N/A | `None` | Returns `None` |
| `test_poor_condition_tag` | Title: `"Roland MC-505 Gebrauchsspuren"` (price 400€) | 400.0 | 27.27% | `"Funcional (Gebrauchsspuren)"` | `"Buen Precio Funcional"` | Condition label set correctly |

#### 2.6 Accessory Tagging
*Rule*: If title contains `ACCESSORY_KEYWORDS` (`"cartridge"`, `"memory"`, `"ram"`, `"rom"`, `"card"`, `"pedal"`, `"expansion"`), `condition_label` is prefixed with `"Accesorio / "` and `discount_str` is overridden to `"0%"`.

| Test Function Name | Title | Price | Expected Condition Tag | Expected Ahorro % |
|-------------------|-------|-------|------------------------|-------------------|
| `test_accessory_memory_card` | `"Roland MC-505 with Memory Card"` | `400.0` | `"Accesorio / Funcional (Average)"` | `"0%"` |

#### 2.7 Thomann B-Stock Source Handling
*Rule*: Listings with `source == 'Thomann B-Stock'` always produce an opportunity tagged `"Thomann B-Stock Deal"`.

| Test Function Name | Title | Source | Price | Expected Opportunity | Expected Platform |
|-------------------|-------|--------|-------|----------------------|-------------------|
| `test_thomann_bstock_opportunity` | `"Roland MC-505"` | `'Thomann B-Stock'` | `500.0` | `"Thomann B-Stock Deal"` | `'Thomann B-Stock'` |

---

### Catalog Section 3: `SupabaseDB` Unit Tests (`test_supabase.py`)

| Test Function Name | Setup / Condition | Action | Assertion / Verification |
|-------------------|-------------------|--------|--------------------------|
| `test_supabase_init_no_env_vars` | Clear `SUPABASE_URL` & `SUPABASE_KEY` env vars | Instantiate `SupabaseDB()` | `db.client` is `None`, warning logged |
| `test_map_to_db` | Python listing dict with Spanish keys | Call `db._map_to_db(item)` | Output dict has DB keys (`url`, `modelo`, `precio`, etc.) |
| `test_map_from_db` | DB item dict with column names | Call `db._map_from_db(item)` | Output dict has Spanish keys (`Enlace`, `Modelo`, `Precio URL`, etc.) |
| `test_upsert_listings_success` | Mocked `create_client` | Call `db.upsert_listings([item])` | Verifies `table("listings").upsert(...)` executed and returns data |
| `test_upsert_listings_empty_input` | Mocked `create_client` | Call `db.upsert_listings([])` | Returns `[]` without calling Supabase API |
| `test_get_listings_success` | Mocked `create_client` returning DB records | Call `db.get_listings()` | Returns list of mapped Python dicts |

---

### Catalog Section 4: Integration Tests (`test_integration.py`)

| Test Function Name | Target Function | Mock Fixtures Used | Assertion / Verification |
|-------------------|-----------------|--------------------|--------------------------|
| `test_scrape_kleinanzeigen_brand_integration` | `scrape_kleinanzeigen_brand` | `mock_playwright_browser`, HTML with 1 valid deal & 1 junk ad | Returns 1 valid listing, filters junk ad, skips duplicates |
| `test_scrape_ebay_brand_integration` | `scrape_ebay_brand` | `mock_playwright_page`, eBay card HTML snippet | Extracts price from eBay HTML, returns valid opportunity |
| `test_scrape_thomann_bstock_integration` | `scrape_thomann_bstock` | `mock_playwright_browser`, Thomann B-Stock HTML snippet | Parses B-Stock card, returns Thomann deal |
| `test_main_async_integration` | `main_async` | Mocked `scrape_all_platforms` & `SupabaseDB` | Executes full workflow, calls `upsert_listings`, finishes in < 50ms |

---

## 4. Verification & Execution Plan

To run and verify the test suite when implemented:
```bash
# Execute entire pytest test suite with verbose output
pytest tests/ -v

# Execute with coverage report
pytest tests/ --cov=synth_arbitrage --cov=supabase_client
```
