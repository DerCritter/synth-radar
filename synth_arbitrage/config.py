"""Configuration module for SynthRadar arbitrage system.

Contains keyword filter lists, target brand definitions, baseline market values,
and thread-safe/atomic JSON configuration persistence utilities.
"""

import json
import logging
import os
import tempfile
from typing import Any, Dict, List, Optional, Tuple

JUNK_KEYWORDS: List[str] = [
    "case", "flightcase", "cover", "dust", "decksaver", "manual", "anleitung", 
    "knob", "fader", "pot", "psu", "power supply", "netzteil", "cable", "kabel", 
    "stand", "ständer", "gigbag", "bag", "tasche", "box", "ovp", "box only", 
    "decal", "sticker", "trafo", "transformer", "transformador", "seitenteile", 
    "holzseitenteile", "wood panels", "wooden sides", "rack ears", "rackmount", 
    "holz", "wood", "stromkabel"
]

ACCESSORY_KEYWORDS: List[str] = [
    "cartridge", "memory", "ram", "rom", "card", "pedal", "expansion", 
    "voice", "voice card"
]

DEFECTIVE_KEYWORDS: List[str] = [
    "defekt", "bastler", "parts", "repair", "reparieren"
]

CONDITION_DEFEKT: List[str] = [
    "defekt", "bastler", "ersatzteile", "reparaturbedürftig", "dachbodenfund", "teildefekt"
]

CONDITION_MINT: List[str] = [
    "mint", "neuwertig", "wie neu", "sammlerzustand", "makellos", "perfekt"
]

CONDITION_POOR: List[str] = [
    "gebrauchsspuren", "kratzer", "dellen", "mängel", "abnutzung", "worn"
]

CONDITION_IGNORE: List[str] = [
    "suche", "tausche", "leerkarton", "manual", "anleitung", "flightcase", "case", 
    "decksaver", "dustcover", "ständer", "stand", "kabel", "tasche", "bag",
    "plugin", "software", "vst", "clone", "behringer", "buch", "handbuch",
    "ramkarte", "netzteil", "ersatzteil", "spare", "part", "knöpfe", "tasten",
    "kappe", "stecker", "lader", "anreize", "ovp nur"
]

TARGET_BRANDS: List[str] = [
    "Roland", "Korg", "Yamaha", "Waldorf", "Kawai", "E-mu", "Akai", 
    "Ensoniq", "Oberheim", "Casio", "Alesis", "Sequential", "Moog", 
    "Nord", "Arturia", "Novation", "Elektron", "Access",
    "Quasimidi", "Kurzweil", "Hohner", "Crumar", "Vermona", "Simmons"
]

# Estimated market value ranges in EUR/USD (low, high)
MARKET_VALUES: Dict[str, Tuple[int, int]] = {
    # ROLAND
    "Roland Juno-106": (1800, 2400), "Roland Jupiter-8": (22000, 28000), "Roland Juno-60": (3000, 4000),
    "Roland TR-808": (4500, 5500), "Roland TR-909": (4000, 5000), "Roland SP-404": (350, 450), "Roland TB-303": (3000, 4000),
    "Roland Alpha Juno": (600, 800), "Roland D-50": (500, 700), "Roland JD-800": (1000, 1400), "Roland Juno-DS": (400, 600),
    "Roland JP-8000": (800, 1000), "Roland System-8": (1000, 1200), "Roland Boutique": (250, 350), "Roland JD-XA": (1100, 1300),
    "Roland MC-303": (180, 280), "Roland MC-505": (450, 650), "Roland MC-707": (600, 750), "Roland JP-8080": (950, 1200),
    "Roland V-Synth": (1200, 1500), "Roland JV-1080": (300, 400), "Roland JV-2080": (450, 600),

    # KORG
    "Korg MS-20": (1100, 1500), "Korg Polysix": (1600, 2200), "Korg M1": (450, 650), "Korg Electribe": (300, 450),
    "Korg Mono/Poly": (2200, 2800), "Korg Wavestation": (400, 550), "Korg Minilogue": (340, 420), "Korg Opsix": (400, 550),
    "Korg Triton": (450, 650), "Korg Kronos": (1800, 2400), "Korg Volca": (90, 150),
    "Korg Volca FM": (100, 140), "Korg Volca Keys": (90, 130), "Korg Volca Bass": (90, 130),
    "Korg Volca Sample": (85, 125), "Korg Volca Beats": (80, 120), "Korg Volca Nubass": (110, 150),
    "Korg Volca Drum": (100, 140), "Korg Volca Modular": (120, 160), "Korg Microkorg": (220, 300),
    "Korg Electribe EMX-1": (550, 750), "Korg Electribe ESX-1": (550, 750), "Korg Electribe 2": (220, 300),
    "Korg Minilogue XD": (400, 550), "Korg Monologue": (200, 250), "Korg Drumlogue": (380, 480), "Korg Modwave": (400, 550),
    "Korg Wavestate": (400, 550), "Korg Prologue": (850, 1100), "Korg NTS-1": (70, 110),

    # YAMAHA
    "Yamaha DX7": (600, 850), "Yamaha CS-80": (25000, 35000), "Yamaha AN1x": (700, 950), "Yamaha SY77": (450, 600),
    "Yamaha Reface CS": (320, 450), "Yamaha Reface DX": (320, 450), "Yamaha Motif": (800, 1100), "Yamaha RX11": (250, 350),
    "Yamaha CS-15": (900, 1200), "Yamaha DX21": (250, 350), "Yamaha SY99": (800, 1100), "Yamaha Montage": (2100, 2600),
    "Yamaha DX200": (650, 850), "Yamaha AN200": (550, 700), "Yamaha CS1x": (180, 280), "Yamaha CS2x": (220, 350),

    # WALDORF
    "Waldorf Blofeld": (300, 340), "Waldorf Micro Q": (350, 450), "Waldorf Pulse": (300, 400), "Waldorf Microwave": (1600, 2000),
    "Waldorf Iridium": (1800, 2000), "Waldorf Quantum": (2600, 3000), "Waldorf Streichfett": (160, 200),

    # KAWAI
    "Kawai K1": (180, 220), "Kawai K4": (220, 280), "Kawai SX-240": (1200, 1600), "Kawai K5000": (900, 1100),

    # E-MU
    "E-mu Proteus": (120, 180), "E-mu Orbit": (220, 280), "E-mu SP-1200": (6000, 8000), "E-mu Emulator": (3500, 4500),

    # AKAI
    "Akai MPC 2000": (700, 900), "Akai MPC 60": (2200, 2800), "Akai S950": (900, 1100), "Akai S1000": (450, 550),
    "Akai MPC Live": (550, 650), "Akai Force": (650, 750), "Akai MPC One": (450, 550),

    # ENSONIQ
    "Ensoniq ESQ-1": (600, 800), "Ensoniq ASR-10": (1300, 1700), "Ensoniq VFX": (450, 550), "Ensoniq Fizmo": (4000, 5000),

    # OBERHEIM
    "Oberheim OB-Xa": (7000, 9000), "Oberheim Matrix": (1100, 1300), "Oberheim DX": (1300, 1700), "Oberheim OB-6": (1900, 2300),

    # CASIO (Pro)
    "Casio CZ-101": (300, 400), "Casio CZ-5000": (550, 650), "Casio FZ-1": (350, 450), "Casio VZ-1": (450, 550),

    # ELEKTRON
    "Elektron Digitakt": (500, 600), "Elektron Digitone": (500, 600), "Elektron Octatrack": (850, 950), "Elektron Analog Rytm": (1100, 1300),
    "Elektron Model:Samples": (220, 280), "Elektron Model:Cycles": (220, 280),

    # MOOG
    "Moog Minimoog Model D": (5500, 6500), "Moog Sub 37": (1400, 1600), "Moog Mother-32": (450, 550), "Moog Matriarch": (1500, 1700),
    "Moog Grandmother": (750, 850), "Moog DFAM": (450, 550),

    # NORD / CLAVIA
    "Nord Lead": (700, 900), "Nord Stage": (1600, 2000), "Nord Electro": (1100, 1300), "Nord Drum": (350, 450),

    # ARTURIA
    "Arturia MicroFreak": (220, 280), "Arturia MatrixBrute": (1400, 1600), "Arturia PolyBrute": (1800, 2000), "Arturia MiniBrute": (250, 350),

    # ALESIS
    "Alesis Andromeda A6": (4000, 5000), "Alesis HR-16": (180, 220), "Alesis SR-16": (100, 140), "Alesis Quadrasynth": (180, 220),

    # SEQUENTIAL / DSI
    "Sequential Prophet": (3000, 3400), "Sequential Drumtraks": (1300, 1700), "Sequential Take 5": (900, 1100)
}


def safe_json_write(data: Any, filepath: str) -> None:
    """Atomically writes JSON data to a file using a temporary file.

    Args:
        data: Data structure to serialize to JSON.
        filepath: Target destination filepath.
    """
    dir_name = os.path.dirname(os.path.abspath(filepath)) or "."
    os.makedirs(dir_name, exist_ok=True)
    temp_fd, temp_path = tempfile.mkstemp(dir=dir_name, prefix="cfg_tmp_", suffix=".json")
    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, filepath)
    except Exception as e:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        logging.error(f"Failed to safely write JSON to {filepath}: {e}")
        raise


def safe_json_read(filepath: str, default: Optional[Any] = None) -> Any:
    """Safely reads JSON data from a file with fallback on error.

    Args:
        filepath: Path to the JSON file to read.
        default: Default value returned if file reading fails or file is missing.

    Returns:
        Deserialized JSON object or default value.
    """
    if not os.path.exists(filepath):
        return default
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError, OSError) as e:
        logging.warning(f"Error reading JSON from {filepath}: {e}")
        return default


def load_or_create_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """Loads configuration from JSON or creates a default config file if absent.

    Args:
        config_file: Optional path to configuration file. Defaults to config.json in root.

    Returns:
        Dict representing current configuration options.
    """
    if config_file is None:
        config_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")

    config = safe_json_read(config_file)
    if not isinstance(config, dict):
        config = {
            "brands": {brand: True for brand in TARGET_BRANDS}
        }
        safe_json_write(config, config_file)
        return config

    if "brands" not in config:
        config["brands"] = {brand: True for brand in TARGET_BRANDS}

    added_new = False
    for brand in TARGET_BRANDS:
        if brand not in config.get("brands", {}):
            config["brands"][brand] = True
            added_new = True

    if added_new:
        safe_json_write(config, config_file)

    return config
