# Comprehensive Business Logic Analysis & Refactoring Plan: `synth_arbitrage.py`

**Author**: Explorer 1  
**Project**: SynthRadar Refactoring & Testing Project (Milestone 1)  
**Target File**: `synth_arbitrage.py`  
**Date**: 2026-07-29  

---

## 1. Executive Summary

This report presents a thorough investigation of the business logic, configuration management, filtering rules, valuation logic, and analysis algorithms in `synth_arbitrage.py`. The primary goal of Milestone 1 is to decouple pure business logic from network scraping (Playwright/BeautifulSoup) and database persistence (Supabase), enabling 100% isolated unit testing and clean modular architecture.

---

## 2. Examination of Business Logic & Keyword Filtering Rules

### 2.1 Keyword Arrays & Lists

`synth_arbitrage.py` contains 7 key keyword lists and 1 brand target list:

1. **`JUNK_KEYWORDS`** (`lines 21-26`):
   - **Keywords**: `"case"`, `"flightcase"`, `"cover"`, `"dust"`, `"decksaver"`, `"manual"`, `"anleitung"`, `"knob"`, `"fader"`, `"pot"`, `"psu"`, `"power supply"`, `"netzteil"`, `"cable"`, `"kabel"`, `"stand"`, `"ständer"`, `"gigbag"`, `"bag"`, `"tasche"`, `"box"`, `"ovp"`, `"box only"`, `"decal"`, `"sticker"`.
   - **Logic**: Evaluated against `title_lower` using word boundary regex `\b{re.escape(junk)}\b`. If matched, the listing is discarded immediately (`return None`).

2. **`CONDITION_IGNORE`** (`lines 40-46`):
   - **Keywords**: `"suche"`, `"tausche"`, `"leerkarton"`, `"manual"`, `"anleitung"`, `"flightcase"`, `"case"`, `"decksaver"`, `"dustcover"`, `"ständer"`, `"stand"`, `"pedal"`, `"kabel"`, `"tasche"`, `"bag"`, `"plugin"`, `"software"`, `"vst"`, `"clone"`, `"behringer"`, `"buch"`, `"handbuch"`, `"ramkarte"`, `"cartridge"`, `"netzteil"`, `"ersatzteil"`, `"spare"`, `"part"`, `"knöpfe"`, `"tasten"`, `"kappe"`, `"stecker"`, `"lader"`, `"anreize"`, `"ovp nur"`.
   - **Logic**: Evaluated against `title_lower` using `\b{ignore}\b`. If matched, listing is discarded (`return None`). Prevents unwanted non-instrument items or wanted ads ("Suche").

3. **`ACCESSORY_KEYWORDS`** (`lines 28-30`):
   - **Keywords**: `"cartridge"`, `"memory"`, `"ram"`, `"rom"`, `"card"`, `"pedal"`, `"expansion"`.
   - **Logic**: If listing passes initial filters and qualifies as an opportunity, `title_lower` is checked. If matched, `condition_label` is prefixed with `"Accesorio / "` and `Ahorro %` is overridden to `"0%"`.

4. **`DEFECTIVE_KEYWORDS`** (`lines 32-34`):
   - **Keywords**: `"defekt"`, `"bastler"`, `"parts"`, `"repair"`, `"reparieren"`.
   - **Logic**: Checked against `title_lower` to mark listing as defective (`is_defekt = True`).

5. **`CONDITION_DEFEKT`** (`line 36`):
   - **Keywords**: `"defekt"`, `"bastler"`, `"ersatzteile"`, `"reparaturbedürftig"`, `"dachbodenfund"`, `"teildefekt"`.
   - **Logic**: Checked against both `title_lower` and `desc_lower` to set `is_defekt = True`.

6. **`CONDITION_MINT`** (`line 37`):
   - **Keywords**: `"mint"`, `"neuwertig"`, `"wie neu"`, `"sammlerzustand"`, `"makellos"`, `"perfekt"`.
   - **Logic**: Checked against `title_lower` and `desc_lower` to set `is_mint = True`.

7. **`CONDITION_POOR`** (`line 38`):
   - **Keywords**: `"gebrauchsspuren"`, `"kratzer"`, `"dellen"`, `"mängel"`, `"abnutzung"`, `"worn"`.
   - **Logic**: Checked against `title_lower` and `desc_lower` to set `is_poor = True`.

8. **`TARGET_BRANDS`** (`lines 48-53`):
   - **Brands**: 24 major synth brands (Roland, Korg, Yamaha, Waldorf, Kawai, E-mu, Akai, Ensoniq, Oberheim, Casio, Alesis, Sequential, Moog, Nord, Arturia, Novation, Elektron, Access, Quasimidi, Kurzweil, Hohner, Crumar, Vermona, Simmons).
   - **Logic**: Used for scraping query generation, configuration auto-migration, and Thomann B-Stock brand filtering.

---

### 2.2 Market Value Mapping & Market Price Retrieval

- **`MARKET_VALUES`** (`lines 56-121`):
  - Dictionary mapping synth model names (e.g. `"Roland Juno-106"`) to expected used market price ranges as tuples `(low_eur, high_eur)`.
  - Example entries:
    - `"Roland Juno-106": (1800, 2400)`
    - `"Korg Minilogue": (340, 420)`
    - `"Yamaha DX7": (600, 850)`
    - `"Moog Minimoog Model D": (5500, 6500)`

- **`get_market_price(model_name)`** (`lines 156-168`):
  - Searches `MARKET_VALUES` keys for a match where `key.lower()` is in `model_name.lower()`.
  - Returns `(low, high)` tuple if tuple in map, or computes `(int(val * 0.85), int(val * 1.15))` for single numbers.
  - Returns `(0, 0)` if no match found.

---

### 2.3 Price Extraction Algorithm (`extract_price`, lines 170-202)

The `extract_price` function cleans raw string price representations scraped from German marketplaces (Kleinanzeigen, eBay, Thomann).

#### Step-by-Step Flow:
1. **Guard Check**: Returns `None` if string is empty or contains short negotiable price indicator (`"VB"` with `len < 5`).
2. **Currency Cleanup**: Strips `"€"` symbol and trailing whitespace.
3. **Decimal / Thousand Separator Normalization**:
   - Both `,` and `.`: German thousand dot + decimal comma (e.g. `"1.250,50"` -> `"1250.50"`).
   - Only `,`: German decimal comma (e.g. `"450,00"` -> `"450.00"`).
   - Only `.`: Checks if matching `\.\d{3}` (e.g. `"1.200"` -> `"1200"`). Otherwise treats dot as decimal.
4. **RegEx Numeric Extraction**: `re.search(r"(\d+\.?\d*)", clean)` -> parsed float.
5. **Fake / Marker Price Filtering**: Discards prices `<= 10` or symbolic prices in `[123, 1234, 1111, 9999]`.
6. **Exception Safety**: Catches any parsing exceptions and returns `None`.

---

### 2.4 Model Identification & Matching Logic (`analyze_listing`, lines 222-245)

Model matching uses dynamic regular expressions generated from `MARKET_VALUES` keys:

1. Keys from `MARKET_VALUES` are sorted by length in descending order (`all_models.sort(key=len, reverse=True)`). This guarantees specific models match before base models (e.g., `"Korg Minilogue XD"` is checked before `"Korg Minilogue"`).
2. Model names are split on spaces and hyphens (`re.split(r"[\s\-]+", model.lower())`).
3. Each token is escaped and joined using `[\s\-]*`, allowing titles with missing/extra hyphens or spaces to match.
4. Bound with `\b` word boundaries: `pattern = rf"\b{pattern_str}\b"`.
5. First matching model is assigned to `detected_model`. If no match, `analyze_listing` returns `None`.

---

### 2.5 Valuation, Discount Calculation, & Deal Classification

1. **Price Floor**:
   - `price` must be `>= 50`, unless title contains `"reface"` or `"sr-16"`. If below floor, listing is discarded (`return None`).
2. **Reference Price Determination**:
   - `market_low, market_high = get_market_price(detected_model)`
   - `market_avg = (market_low + market_high) / 2`
   - If `is_defekt`: `reference_price = market_low` (defect discount measured against worst-case working price).
   - Else if `is_mint`: `reference_price = market_high` (mint deals measured against top market price).
   - Else: `reference_price = market_avg`.
3. **Discount Calculation**:
   - `discount = (reference_price - price) / reference_price`
4. **Opportunity Rules**:
   - `Thomann B-Stock`: If `source == 'Thomann B-Stock'`, always flagged as `"Thomann B-Stock Deal"`.
   - `Defect Deal`: If `is_defekt` and `discount >= 0.40` (40%+ below low market price), flagged as `"Gran Margen Defecto"`.
   - `Functional Deal`: If `not is_defekt` and `discount >= 0.20` (20%+ below avg reference price), flagged as `"Buen Precio Funcional"`.
   - Otherwise, returns `None`.

---

### 2.6 Draft German Message Generation

For listings that pass opportunity thresholds, draft buyer outreach messages are generated:

- **Defective listing message**:
  ```text
  Hallo, ich interessiere mich für den {detected_model}. Da das Gerät als defekt/Bastlerware angeboten wird und eine Reparatur Zeit sowie Ersatzteile erfordert, würde ich {int(price * 0.85)}€ inkl. Versand anbieten. Wäre das für Sie in Ordnung? MfG.
  ```
  *(Offers 85% of asking price to account for repair effort)*

- **Functional listing message**:
  ```text
  Guten Tag, ist der {detected_model} noch verfügbar? Ich hätte großes Interesse. Befindet er sich in einem voll funktionsfähigen Zustand und wäre ein sicherer Versand möglich? Vielen Dank und beste Grüße.
  ```

---

### 2.7 Configuration Loading & Persistence (`load_or_create_config`, lines 123-149)

- Resolves `config.json` path relative to script directory.
- Reads or initializes brand toggles `{"brands": {brand: True for brand in TARGET_BRANDS}}`.
- Performs auto-migration by adding missing brands from `TARGET_BRANDS` as `True`.
- Currently references `safe_json_write` (stubbed as `pass` at line 151).

---

## 3. Proposed Modular Package Breakdown

We recommend breaking down `synth_arbitrage` into a clean package structure under `synth_arbitrage/`:

```
synth_arbitrage/
├── __init__.py
├── config.py         # Configuration loading, saving, and default constants
├── analysis.py       # Pure analysis, price parsing, model matching, deal evaluation
└── (scrapers / db)   # To be modularized in subsequent milestones
```

### Module Responsibilities:

1. **`synth_arbitrage/config.py`**:
   - Houses all immutable lists and dictionaries (`JUNK_KEYWORDS`, `ACCESSORY_KEYWORDS`, `DEFECTIVE_KEYWORDS`, `CONDITION_DEFEKT`, `CONDITION_MINT`, `CONDITION_POOR`, `CONDITION_IGNORE`, `TARGET_BRANDS`, `MARKET_VALUES`).
   - Implements robust atomic JSON file reads and writes (`safe_json_read`, `safe_json_write`, `load_or_create_config`).

2. **`synth_arbitrage/analysis.py`**:
   - Houses pure functions with explicit type signatures, docstrings, and zero network/DB side effects.
   - Core functions: `extract_price`, `get_market_price`, `match_model`, `determine_condition`, `calculate_discount`, `generate_draft_message`, `analyze_listing`.

---

## 4. Exact Function Signatures, Type Hints & Docstrings

Below are the exact proposed function signatures, dataclasses/TypedDicts, type hints, and docstrings for `synth_arbitrage/config.py` and `synth_arbitrage/analysis.py`.

### 4.1 Type Definitions (`synth_arbitrage/types.py` or within `analysis.py` & `config.py`)

```python
from typing import TypedDict, Literal, Optional, Dict, Tuple, List, Union

class ListingAnalysis(TypedDict):
    Modelo: str
    Estado: str
    Precio_URL: float
    Precio_Mercado: str
    Ahorro_Pct: str
    Plataforma: str
    Enlace: str
    Imagen: str
    Reverb: str
    Mensaje_Borrador: str
    last_seen: float

ConfigDict = Dict[str, Dict[str, bool]]
MarketValuesMap = Dict[str, Union[Tuple[int, int], float, int]]
```

---

### 4.2 Signatures for `synth_arbitrage/config.py`

```python
from pathlib import Path
from typing import Dict, Any, Union, Optional

def safe_json_read(filepath: Union[str, Path], default: Optional[Any] = None) -> Any:
    """Safely read and parse a JSON file.

    Args:
        filepath: Path to the JSON file to read.
        default: Fallback value returned if file does not exist or fails to parse.

    Returns:
        Parsed JSON data or default value on failure.
    """
    ...

def safe_json_write(data: Any, filepath: Union[str, Path]) -> bool:
    """Atomically write data to a JSON file using a temporary file.

    Args:
        data: Data payload to serialize as JSON.
        filepath: Target destination file path.

    Returns:
        True if write succeeded, False otherwise.
    """
    ...

def load_or_create_config(config_path: Optional[Union[str, Path]] = None) -> Dict[str, Dict[str, bool]]:
    """Load configuration from disk or create default configuration with brand toggles.

    Ensures auto-migration by injecting any newly defined target brands into existing config.

    Args:
        config_path: Path to config JSON file. Defaults to 'config.json' in module directory.

    Returns:
        Configuration dictionary containing brand enable/disable toggles.
    """
    ...
```

---

### 4.3 Signatures for `synth_arbitrage/analysis.py`

```python
from typing import Tuple, Optional, Dict, Union, TypedDict

class ListingAnalysis(TypedDict):
    Modelo: str
    Estado: str
    Precio_URL: float
    Precio_Mercado: str
    Ahorro_Pct: str
    Plataforma: str
    Enlace: str
    Imagen: str
    Reverb: str
    Mensaje_Borrador: str
    last_seen: float

def extract_price(price_str: Optional[str]) -> Optional[float]:
    """Parse raw marketplace price strings into sanitized float numeric values.

    Handles German/European currency formatting (dot thousands, comma decimals),
    strips currency symbols and 'VB' indicators, and filters out symbolic/fake prices
    (e.g., prices <= 10 or markers like 123, 1234, 1111, 9999).

    Args:
        price_str: Raw text price from scraped HTML listing (e.g. '1.250,50 €', '450 € VB').

    Returns:
        Parsed float price if valid, or None if input is unparseable or fake.
    """
    ...

def get_market_price(
    model_name: str, 
    market_values: Optional[Dict[str, Union[Tuple[int, int], float, int]]] = None
) -> Tuple[int, int]:
    """Retrieve the estimated low and high used market prices for a given synth model.

    Args:
        model_name: The name of the synth model.
        market_values: Optional dictionary mapping model names to price tuples (low, high).
                       Defaults to MARKET_VALUES from config module.

    Returns:
        A tuple of (low_price, high_price) in EUR/USD. Returns (0, 0) if model is unknown.
    """
    ...

def match_model(
    title: str, 
    market_values: Optional[Dict[str, Union[Tuple[int, int], float, int]]] = None
) -> Optional[str]:
    """Match listing title against database of synthesizer models using regex patterns.

    Sorts models by length descending to prioritize specific model variants (e.g., 'Minilogue XD'
    over 'Minilogue'). Matches tokens separated by spaces or hyphens flexibly with word boundaries.

    Args:
        title: Listing title string.
        market_values: Optional custom market values dictionary.

    Returns:
        Exact model key string from database if matched, or None if no match found.
    """
    ...

def determine_condition(title: str, description: str) -> Tuple[bool, bool, bool]:
    """Determine listing condition flags (defective, mint, poor) from text content.

    Args:
        title: Listing title string.
        description: Listing description string.

    Returns:
        Tuple of booleans (is_defekt, is_mint, is_poor).
    """
    ...

def calculate_discount(
    price: float, 
    market_low: int, 
    market_high: int, 
    is_defekt: bool, 
    is_mint: bool
) -> Tuple[float, float]:
    """Calculate valuation reference price and savings percentage.

    Args:
        price: Asking listing price.
        market_low: Low market estimate.
        market_high: High market estimate.
        is_defekt: True if listing is defective/bastlerware.
        is_mint: True if listing is in mint condition.

    Returns:
        Tuple of (reference_price, discount_fraction).
    """
    ...

def generate_draft_message(model_name: str, price: float, is_defekt: bool) -> str:
    """Generate draft negotiation/inquiry message in German for seller outreach.

    Args:
        model_name: Detected synthesizer model name.
        price: Asking price.
        is_defekt: True if item is defective (triggers repair discount offer).

    Returns:
        Formatted German draft message string.
    """
    ...

def analyze_listing(
    title: str,
    description: str,
    price: Optional[float],
    url: str,
    image_url: str = "",
    source: str = "Kleinanzeigen",
    market_values: Optional[Dict[str, Union[Tuple[int, int], float, int]]] = None,
    timestamp: Optional[float] = None
) -> Optional[ListingAnalysis]:
    """Analyze a single listing to detect synth model, condition, valuation, and arbitrage deals.

    This pure function performs zero I/O operations, network requests, or database access.
    It evaluates listing titles/descriptions against junk keywords, ignore filters, price thresholds,
    model regexes, condition flags, and discount margins.

    Args:
        title: Listing title text.
        description: Listing body description text.
        price: Parsed numerical asking price (or None).
        url: Direct listing link URL.
        image_url: Listing primary image thumbnail URL. Defaults to "".
        source: Listing platform name (e.g. 'Kleinanzeigen', 'eBay', 'Thomann B-Stock').
        market_values: Optional dictionary override for market values. Defaults to config values.
        timestamp: Optional UNIX timestamp override for deterministic testing. Defaults to current time.

    Returns:
        ListingAnalysis dictionary if listing qualifies as an arbitrage opportunity; None otherwise.
    """
    ...
```

---

## 5. Complete Network & Database Isolation Mechanics

### 5.1 Pure Isolation Guarantee

In the current codebase, `analyze_listing` and `extract_price` rely on zero Playwright pages, BeautifulSoup HTML parsing instances, HTTP requests, or Supabase DB handles.

To ensure 100% test isolation in `synth_arbitrage/analysis.py`:
1. `analyze_listing` takes scalar primitive arguments (`title: str`, `description: str`, `price: float | None`, `url: str`, etc.).
2. In-memory `market_values` and `timestamp` parameters can be explicitly injected, removing any implicit dependency on external state or file system clock.
3. Unit tests can test 100+ edge-case titles, price formats, and defective conditions in milliseconds without initiating any network connections or writing to databases.

### 5.2 Unit Test Matrix & Recommendations

The following test suites should be constructed for `synth_arbitrage/analysis.py`:

| Test Target | Input Case | Expected Result | Reason / Coverage |
|---|---|---|---|
| `extract_price` | `"1.250,00 €"` | `1250.0` | German thousand dot & decimal comma |
| `extract_price` | `"450 € VB"` | `450.0` | Currency symbol & VB indicator stripping |
| `extract_price` | `"VB"` | `None` | Short unparseable VB string |
| `extract_price` | `"1234 €"` | `None` | Fake/symbolic price filter |
| `analyze_listing` | Title: `"Roland Juno 106 Ständer"` | `None` | Filtered by `JUNK_KEYWORDS` / `CONDITION_IGNORE` |
| `analyze_listing` | Title: `"Roland Juno-106 super Zustand"`, Price: `1100.0` | Valid `ListingAnalysis` (Discount ~47%) | Functional deal >= 20% discount |
| `analyze_listing` | Title: `"Roland Juno 106 defekt Bastler"`, Price: `1000.0` | Valid `ListingAnalysis` (Discount ~44%) | Defect deal >= 40% discount vs low price (1800) |
| `analyze_listing` | Title: `"Korg Minilogue XD"`, Price: `350.0` | Model: `"Korg Minilogue XD"` | Length-descending regex matches XD before base Minilogue |

---

## 6. Recommendations & Next Steps for Implementation (Milestone 1)

1. Create `synth_arbitrage/__init__.py` to turn `synth_arbitrage` into a clean Python package.
2. Create `synth_arbitrage/config.py` containing constants, configuration loading, auto-migration, and safe atomic file persistence.
3. Create `synth_arbitrage/analysis.py` containing pure analysis functions with complete type hints and docstrings.
4. Update `synth_arbitrage.py` (or caller modules) to import `analyze_listing`, `extract_price`, and `load_or_create_config` from the new `synth_arbitrage` package.
5. Implement unit tests in `tests/test_analysis.py` verifying all edge cases in complete network/DB isolation.
