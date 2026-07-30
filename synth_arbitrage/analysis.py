"""Analysis and evaluation module for SynthRadar arbitrage logic.

Extracts price values, queries baseline market pricing, tags equipment condition,
calculates discounts, and determines arbitrage opportunity status without external dependencies.
"""

from datetime import datetime
import re
from typing import Any, Dict, List, Optional, Tuple

from synth_arbitrage.config import (
    ACCESSORY_KEYWORDS,
    CONDITION_DEFEKT,
    CONDITION_IGNORE,
    CONDITION_MINT,
    CONDITION_POOR,
    DEFECTIVE_KEYWORDS,
    JUNK_KEYWORDS,
    MARKET_VALUES,
)


def get_market_price(model_name: str) -> Tuple[int, int]:
    """Retrieves baseline market value price range for a given gear model name.

    Args:
        model_name: The target synthesizer or gear model name.

    Returns:
        A tuple of (low_price, high_price) in EUR/USD. Returns (0, 0) if model is unknown.
    """
    sorted_keys = sorted(MARKET_VALUES.keys(), key=len, reverse=True)
    for key in sorted_keys:
        value = MARKET_VALUES[key]
        if key.lower() in model_name.lower():
            if isinstance(value, tuple):
                return value
            else:
                return (int(value * 0.85), int(value * 1.15))
    return (0, 0)


def extract_price(price_str: Optional[str]) -> Optional[float]:
    """Parses numeric price from raw listing price strings.

    Handles German currency formatting (e.g. 1.250,50 € or 450 VB) and removes
    junk text or symbolic placeholder prices. Negative price inputs return None.

    Args:
        price_str: Raw price string from listing scraper.

    Returns:
        Parsed float price if valid, or None if price is invalid, negative, or fake/placeholder.
    """
    if not price_str or ("VB" in price_str and len(price_str) < 5):
        return None
    if re.search(r"-\s*€?\s*\d", price_str):
        return None
    try:
        clean = price_str.replace("€", "").strip()
        if "," in clean and "." in clean:
            clean = clean.replace(".", "").replace(",", ".")
        elif "," in clean:
            clean = clean.replace(",", ".")
        elif "." in clean:
            if re.search(r"\.\d{3}", clean):
                clean = clean.replace(".", "")

        match = re.search(r"(\d+\.?\d*)", clean)
        if not match:
            return None
        price = float(match.group(1))
        if price <= 10 or price in [123, 1234, 1111, 9999]:
            return None
        return price
    except Exception:
        return None


def analyze_listing(
    title: str,
    description: str,
    price: Optional[float],
    url: str,
    image_url: str = "",
    source: str = "Kleinanzeigen"
) -> Optional[Dict[str, Any]]:
    """Analyzes a single equipment listing against known market models and pricing rules.

    Evaluates keyword filters, condition tagging (Defekt, Mint, Gebrauchsspuren),
    discount ratios, and generates automated German message drafts for arbitrage opportunities.
    Has zero network or database dependencies.

    Args:
        title: Title string of the listing.
        description: Description text of the listing.
        price: Cleaned floating point price of the listing.
        url: Direct link to the listing page.
        image_url: Optional image thumbnail URL.
        source: Listing source platform (e.g. Kleinanzeigen, eBay, Thomann B-Stock).

    Returns:
        Dict containing opportunity details if listing qualifies, or None if discarded.
    """
    title_lower = title.lower()
    desc_lower = description.lower()

    # 1. Discard listings containing junk keywords or ignore tags in title
    for junk in JUNK_KEYWORDS:
        if re.search(rf"\b{re.escape(junk)}\b", title_lower):
            return None

    for ignore in CONDITION_IGNORE:
        if re.search(rf"\b{ignore}\b", title_lower):
            return None

    # Filter minimum price threshold unless special model exceptions apply
    if price is None or (price < 50 and "reface" not in title_lower and "sr-16" not in title_lower):
        return None

    # Match exact model from database (sorted by length descending to match longest pattern first)
    all_models = list(MARKET_VALUES.keys())
    clean_title = title_lower
    detected_model = None
    all_models.sort(key=len, reverse=True)

    for model in all_models:
        parts = re.split(r"[\s\-]+", model.lower())
        pattern_str = r"[\s\-]*".join([re.escape(p) for p in parts])
        pattern = rf"\b{pattern_str}\b"

        if re.search(pattern, clean_title):
            detected_model = model
            break

    if not detected_model:
        return None

    # Determine condition state
    is_defekt = any(
        re.search(rf"\b{re.escape(kw)}\b", title_lower) or re.search(rf"\b{re.escape(kw)}\b", desc_lower)
        for kw in CONDITION_DEFEKT
    ) or any(
        re.search(rf"\b{re.escape(kw)}\b", title_lower)
        for kw in DEFECTIVE_KEYWORDS
    )
    is_mint = any(
        re.search(rf"\b{re.escape(kw)}\b", title_lower) or re.search(rf"\b{re.escape(kw)}\b", desc_lower)
        for kw in CONDITION_MINT
    )
    is_poor = any(
        re.search(rf"\b{re.escape(kw)}\b", title_lower) or re.search(rf"\b{re.escape(kw)}\b", desc_lower)
        for kw in CONDITION_POOR
    )

    market_low, market_high = get_market_price(detected_model)
    if market_low == 0:
        return None

    market_avg = (market_low + market_high) / 2.0

    reference_price = market_avg
    if is_defekt:
        reference_price = float(market_low)
    elif is_mint:
        reference_price = float(market_high)

    discount = (reference_price - price) / reference_price

    opportunity = None
    if source == "Thomann B-Stock":
        opportunity = "Thomann B-Stock Deal"
    elif is_defekt and discount >= 0.40:
        opportunity = "Gran Margen Defecto"
    elif not is_defekt and discount >= 0.20:
        opportunity = "Buen Precio Funcional"

    if opportunity:
        is_accessory = any(
            re.search(rf"\b{re.escape(kw)}\b", title_lower)
            for kw in ACCESSORY_KEYWORDS
        )
        
        if is_accessory:
            return None

        if source == "Thomann B-Stock":
            condition_label = "B-Stock / Oficial"
            discount_str = "0%"
        else:
            condition_label = "Funcional (Average)"
            if is_defekt:
                condition_label = "Defekt/Bastler"
            elif is_mint:
                condition_label = "Funcional (Mint)"
            elif is_poor:
                condition_label = "Funcional (Gebrauchsspuren)"

            discount_str = f"{int(discount * 100)}%"

        if is_defekt:
            msg = (
                f"Hallo, ich interessiere mich für den {detected_model}. Da das Gerät als defekt/Bastlerware "
                f"angeboten wird und eine Reparatur Zeit sowie Ersatzteile erfordert, würde ich {int(price * 0.85)}€ "
                f"inkl. Versand anbieten. Wäre das für Sie in Ordnung? MfG."
            )
        else:
            msg = (
                f"Guten Tag, ist der {detected_model} noch verfügbar? Ich hätte großes Interesse. Befindet er "
                f"sich in einem voll funktionsfähigen Zustand und wäre ein sicherer Versand möglich? Vielen Dank und beste Grüße."
            )

        return {
            "Modelo": detected_model,
            "Estado": condition_label,
            "Precio URL": price,
            "Precio Mercado": f"{int(market_low)} - {int(market_high)} €",
            "Ahorro %": discount_str,
            "Plataforma": source,
            "Enlace": url,
            "Imagen": image_url,
            "Reverb": f"https://reverb.com/marketplace?query={detected_model.replace(' ', '+')}&condition=used",
            "Mensaje Borrador": msg,
            "last_seen": datetime.now().timestamp(),
        }

    return None
