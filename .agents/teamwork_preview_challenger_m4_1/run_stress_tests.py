"""Empirical stress test suite for SynthRadar analysis, price extraction, market lookup, and SupabaseDB."""

import os
import sys
import time
import json
from typing import Any, Dict, List
from unittest.mock import MagicMock

# Ensure synth_arbitrage is importable from project root
sys.path.insert(0, "/Users/dacritter/.gemini/antigravity/playground/pulsing-perseverance")

from synth_arbitrage.analysis import analyze_listing, extract_price, get_market_price
from synth_arbitrage.config import MARKET_VALUES, JUNK_KEYWORDS, CONDITION_IGNORE, ACCESSORY_KEYWORDS
from synth_arbitrage.database import SupabaseDB


def run_tests() -> Dict[str, Any]:
    results = {
        "scenario_1_model_collisions": [],
        "scenario_2_price_parsing": [],
        "scenario_3_keyword_boundaries": [],
        "scenario_4_supabase_db": [],
        "performance": {},
    }

    # ==========================================
    # SCENARIO 1: REGEX MODEL COLLISION EDGE CASES & MARKET LOOKUP BUGS
    # ==========================================
    print("--- Running Scenario 1: Model Collision Edge Cases ---")

    # Test 1a: Model lookup priority in get_market_price
    # Test "Korg Minilogue XD" vs "Korg Minilogue"
    mp_minilogue_xd = get_market_price("Korg Minilogue XD")
    expected_xd = MARKET_VALUES["Korg Minilogue XD"]
    results["scenario_1_model_collisions"].append({
        "test": "get_market_price('Korg Minilogue XD')",
        "got": mp_minilogue_xd,
        "expected": expected_xd,
        "pass": mp_minilogue_xd == expected_xd,
        "issue": None if mp_minilogue_xd == expected_xd else "BUG: get_market_price matched 'Korg Minilogue' first due to dict ordering!"
    })

    # Test Korg Electribe EMX-1 vs Korg Electribe
    mp_emx1 = get_market_price("Korg Electribe EMX-1")
    expected_emx1 = MARKET_VALUES["Korg Electribe EMX-1"]
    results["scenario_1_model_collisions"].append({
        "test": "get_market_price('Korg Electribe EMX-1')",
        "got": mp_emx1,
        "expected": expected_emx1,
        "pass": mp_emx1 == expected_emx1,
        "issue": None if mp_emx1 == expected_emx1 else "BUG: get_market_price matched 'Korg Electribe' first!"
    })

    # Test Korg Electribe ESX-1 vs Korg Electribe
    mp_esx1 = get_market_price("Korg Electribe ESX-1")
    expected_esx1 = MARKET_VALUES["Korg Electribe ESX-1"]
    results["scenario_1_model_collisions"].append({
        "test": "get_market_price('Korg Electribe ESX-1')",
        "got": mp_esx1,
        "expected": expected_esx1,
        "pass": mp_esx1 == expected_esx1,
        "issue": None if mp_esx1 == expected_esx1 else "BUG: get_market_price matched 'Korg Electribe' first!"
    })

    # Test 1b: analyze_listing with "Roland Juno-106 case"
    res_juno_case = analyze_listing("Roland Juno-106 case", "Great condition", 1000.0, "http://example.com/1")
    results["scenario_1_model_collisions"].append({
        "test": "analyze_listing('Roland Juno-106 case')",
        "got": res_juno_case,
        "expected": None,
        "pass": res_juno_case is None,
        "issue": None if res_juno_case is None else "Failed to discard listing with case in title"
    })

    # Test 1c: analyze_listing with "Yamaha CS-80 clone"
    res_cs80_clone = analyze_listing("Yamaha CS-80 clone", "Great clone synth", 5000.0, "http://example.com/2")
    results["scenario_1_model_collisions"].append({
        "test": "analyze_listing('Yamaha CS-80 clone')",
        "got": res_cs80_clone,
        "expected": None,
        "pass": res_cs80_clone is None,
        "issue": None if res_cs80_clone is None else "Failed to discard clone listing"
    })

    # Test 1d: analyze_listing with "Korg Minilogue XD" vs "Korg Minilogue"
    res_xd = analyze_listing("Korg Minilogue XD Synthesizer", "Top condition", 350.0, "http://example.com/xd")
    # Real Minilogue XD market avg = (400+550)/2 = 475. Price 350 => discount = (475-350)/475 = 26.3% >= 20% -> Valid!
    # Flawed get_market_price returns (340, 420), avg = 380. Price 350 => discount = (380-350)/380 = 7.89% < 20% -> Discarded!
    results["scenario_1_model_collisions"].append({
        "test": "analyze_listing('Korg Minilogue XD Synthesizer', price=350.0)",
        "got_model": res_xd["Modelo"] if res_xd else None,
        "got_market_price": res_xd["Precio Mercado"] if res_xd else None,
        "got_result": res_xd is not None,
        "expected_result": True,
        "pass": res_xd is not None and res_xd.get("Precio Mercado") == "400 - 550 €",
        "issue": "BUG: Discarded valid Minilogue XD opportunity due to flawed market price lookup returning 340 - 420 €!" if res_xd is None or res_xd.get("Precio Mercado") != "400 - 550 €" else None
    })

    # ==========================================
    # SCENARIO 2: EXTREME PRICE PARSING INPUTS
    # ==========================================
    print("--- Running Scenario 2: Extreme Price Parsing Inputs ---")

    price_inputs = [
        ("1.250,50 €", 1250.5),
        ("0 €", None),
        ("-50 €", None),
        ("99999 €", 99999.0),
        ("123 €", None),
        ("450 € VB", 450.0),
        ("VB", None),
        ("", None),
        (None, None),
        # Additional extreme edge cases
        ("-1250 €", None),
        ("1,250.00 €", 1250.0), # US format test
        ("1.250.000 €", 1250000.0),
        ("0,00 €", None),
        ("10 €", None),
        ("10,01 €", 10.01),
        ("VB 450", 450.0),
        ("VB 4", None), # len < 5 with VB
        ("VB 45", 45.0), # len >= 5 with VB
    ]

    for p_in, exp in price_inputs:
        got = extract_price(p_in)
        passed = got == exp
        issue = None
        if not passed:
            if p_in in ["-50 €", "-1250 €"] and got is not None and got > 0:
                issue = f"BUG: Negative price '{p_in}' parsed as POSITIVE {got}!"
            elif p_in == "1,250.00 €":
                issue = f"BUG: US decimal format '1,250.00 €' parsed as {got}!"
            else:
                issue = f"Parsed '{p_in}' as {got}, expected {exp}"

        results["scenario_2_price_parsing"].append({
            "input": p_in,
            "got": got,
            "expected": exp,
            "pass": passed,
            "issue": issue
        })

    # ==========================================
    # SCENARIO 3: KEYWORD BOUNDARY TESTS & SUBSTRING MATCHING
    # ==========================================
    print("--- Running Scenario 3: Keyword Boundary & Substring Tests ---")

    kw_tests = [
        # Word boundary tests for junk/ignore
        ("Roland Juno-106 ministry edition", "Ministry title test", 1000.0, True, "ministry shouldn't trigger junk/ignore"),
        ("Roland Juno-106 mini synth", "Mini synth test", 1000.0, True, "mini shouldn't trigger junk/ignore"),
        ("Roland Juno-106 anleitung", "Anleitung test", 1000.0, False, "anleitung triggers junk/ignore"),
        ("Roland Juno-106 ohne Anleitung", "Selling synth without manual", 1000.0, True, "BUG: 'ohne Anleitung' (without manual) causes synth listing to be discarded!"),
        ("Roland Juno-106 service manual included", "Manual test", 1000.0, False, "manual triggers junk/ignore"),
        ("Roland Juno-106 (no manual)", "No manual test", 1000.0, True, "BUG: '(no manual)' causes synth listing to be discarded!"),
        
        # Substring false positives in condition tagging
        ("Roland Juno-106 nicht defekt", "Explicitly NOT defective in title", 1000.0, "Funcional (Average)", "BUG: Substring 'defekt' in 'nicht defekt' falsely tags as Defekt!"),
        ("Roland Juno-106", "Gerät ist nicht defekt", 1000.0, "Funcional (Average)", "BUG: Substring 'defekt' in description 'nicht defekt' falsely tags as Defekt!"),
        ("Roland Juno-106 unter allen Modellen das Beste", "Word 'Modellen' in title", 1000.0, "Funcional (Average)", "BUG: Substring 'dellen' inside 'Modellen' falsely tags as Gebrauchsspuren!"),
        ("Roland Juno-106 ohne Mängel", "Word 'ohne Mängel' in description", 1000.0, "Funcional (Average)", "BUG: Substring 'mängel' inside 'ohne Mängel' falsely tags as Gebrauchsspuren!"),
        ("Roland Juno-106 Synthesizer Program", "Word 'Program' in title", 1000.0, "Funcional (Average)", "BUG: Substring 'ram' inside 'Program' falsely tags as Accessory and sets discount to 0%!"),
        ("Roland Juno-106 direct from studio", "Word 'from' in title", 1000.0, "Funcional (Average)", "BUG: Substring 'rom' inside 'from' falsely tags as Accessory and sets discount to 0%!"),
        
        # Unreachable accessory code test (cartridge & pedal in CONDITION_IGNORE)
        ("Roland Juno-106 cartridge included", "Cartridge test", 1000.0, "Accesorio / Funcional (Average)", "BUG: 'cartridge' is in CONDITION_IGNORE, so listing discarded instead of tagged as accessory!"),
    ]

    for title, desc_or_test_name, price, exp_state_or_pass, note in kw_tests:
        res = analyze_listing(title, desc_or_test_name, price, "http://example.com/kw")
        if isinstance(exp_state_or_pass, bool):
            passed = (res is not None) == exp_state_or_pass
            got_str = "Accepted" if res else "Discarded"
            exp_str = "Accepted" if exp_state_or_pass else "Discarded"
        else:
            got_str = res["Estado"] if res else "Discarded"
            exp_str = exp_state_or_pass
            passed = got_str == exp_str

        results["scenario_3_keyword_boundaries"].append({
            "title": title,
            "test_note": note,
            "got": got_str,
            "expected": exp_str,
            "pass": passed,
            "issue": None if passed else note
        })

    # ==========================================
    # SCENARIO 4: SUPABASE DB EDGE CASES & STRESS
    # ==========================================
    print("--- Running Scenario 4: SupabaseDB Tests ---")

    db = SupabaseDB()
    
    # 4a. Missing env vars fallback
    db_no_env = SupabaseDB()
    db_no_env.client = None
    res_upsert_none = db_no_env.upsert_listings([{"Modelo": "Test"}])
    res_get_empty = db_no_env.get_listings()
    results["scenario_4_supabase_db"].append({
        "test": "SupabaseDB missing client fallback",
        "upsert_result": res_upsert_none,
        "get_result": res_get_empty,
        "pass": res_upsert_none is None and res_get_empty == [],
        "issue": None
    })

    # 4b. Mapping edge cases (empty dict, None fields, extra fields)
    empty_map_to = db._map_to_db({})
    empty_map_from = db._map_from_db({})
    results["scenario_4_supabase_db"].append({
        "test": "_map_to_db({}) and _map_from_db({})",
        "map_to_keys": len(empty_map_to),
        "map_from_keys": len(empty_map_from),
        "pass": all(v is None for v in empty_map_to.values()) and all(v is None for v in empty_map_from.values()),
        "issue": None
    })

    # 4c. Exception handling in upsert_listings & get_listings
    mock_client = MagicMock()
    db.client = mock_client
    mock_client.table.side_effect = Exception("Supabase connection timeout")
    
    upsert_exc = db.upsert_listings([{"Modelo": "Test"}])
    get_exc = db.get_listings()

    results["scenario_4_supabase_db"].append({
        "test": "SupabaseDB exception handling",
        "upsert_on_exc": upsert_exc,
        "get_on_exc": get_exc,
        "pass": upsert_exc is None and get_exc == [],
        "issue": None if upsert_exc is None and get_exc == [] else "Failed to handle Supabase DB exception gracefully"
    })

    # ==========================================
    # PERFORMANCE & EXECUTION CHECKS
    # ==========================================
    print("--- Running Performance Checks ---")

    # Measure execution time for 10,000 analyze_listing calls
    t0 = time.perf_counter()
    for i in range(10000):
        analyze_listing("Roland Juno-106 Synthesizer Top Zustand", "Voll funktionsfähig studio use", 1200.0, "http://example.com")
    t1 = time.perf_counter()
    duration = t1 - t0
    ops_per_sec = 10000 / duration

    results["performance"] = {
        "iterations": 10000,
        "total_seconds": round(duration, 4),
        "ops_per_second": round(ops_per_sec, 2),
        "pass": duration < 2.0  # Should process 10,000 listings in under 2 seconds
    }

    return results


if __name__ == "__main__":
    res = run_tests()
    print("\n" + "="*50)
    print("STRESS TEST SUMMARY RESULTS:")
    print("="*50)
    print(json.dumps(res, indent=2))
