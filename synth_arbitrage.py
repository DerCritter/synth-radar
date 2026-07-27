import time
import logging
import re
import json
import os
import shutil
import tempfile
from supabase_client import SupabaseDB
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from tabulate import tabulate

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# La lista de modelos ahora se carga dinámicamente desde config.json
# basado en MARKET_VALUES

CONDITION_DEFEKT = ["defekt", "bastler", "ersatzteile", "reparaturbedürftig", "dachbodenfund", "teildefekt"]
CONDITION_MINT = ["mint", "neuwertig", "wie neu", "sammlerzustand", "makellos", "perfekt"]
CONDITION_POOR = ["gebrauchsspuren", "kratzer", "dellen", "mängel", "abnutzung", "worn"]

CONDITION_IGNORE = [
    "suche", "tausche", "leerkarton", "manual", "anleitung", "flightcase", "case", 
    "decksaver", "dustcover", "ständer", "stand", "pedal", "kabel", "tasche", "bag",
    "plugin", "software", "vst", "clone", "behringer", "buch", "handbuch",
    "ramkarte", "cartridge", "netzteil", "ersatzteil", "spare", "part", "knöpfe", "tasten",
    "kappe", "stecker", "lader", "anreize", "ovp nur"
]

TARGET_BRANDS = [
    "Roland", "Korg", "Yamaha", "Waldorf", "Kawai", "E-mu", "Akai", 
    "Ensoniq", "Oberheim", "Casio", "Alesis", "Sequential", "Moog", 
    "Nord", "Arturia", "Novation", "Elektron", "Access",
    "Quasimidi", "Kurzweil", "Hohner", "Crumar", "Vermona", "Simmons"
]

# Precios de mercado promedios estimados (USD/EUR) 
MARKET_VALUES = {
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
    "Korg Triton": (450, 650), "Korg Kronos": (1800, 2400), "Korg Volca": (90, 150), "Korg Microkorg": (220, 300),
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

def load_or_create_config():
    config_file = os.path.join(os.path.dirname(__file__), "config.json")
    
    if not os.path.exists(config_file):
        config = {
            "brands": {brand: True for brand in TARGET_BRANDS}
        }
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        return config
    else:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
            
            # Auto-migrate dictionary format if needed
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

def safe_json_write(data, filepath):
    pass

def safe_json_read(filepath, default=None):
    return default

def get_market_price(model_name):
    """
    Simula la consulta a la Guía de Precios de Reverb.
    Ahora devuelve un rango (mínimo, máximo).
    """
    for key, value in MARKET_VALUES.items():
        if key.lower() in model_name.lower():
            if isinstance(value, tuple):
                return value
            else:
                # Si es un valor único, generamos un rango coherente (-15% / +15%)
                return (int(value * 0.85), int(value * 1.15))
    return (0, 0)

def extract_price(price_str):
    if not price_str or ("VB" in price_str and len(price_str) < 5):
        return None
    try:
        # Remueve el signo del Euro y limpia espacios
        clean = price_str.replace("€", "").strip()
        # Kleinanzeigen usa "." para miles y "," para decimales, o nada.
        # Caso 1: 1.250,50 -> 1250.50
        # Caso 2: 450 -> 450
        if "," in clean and "." in clean:
            clean = clean.replace(".", "").replace(",", ".")
        elif "," in clean:
            clean = clean.replace(",", ".")
        elif "." in clean:
            # Si solo hay un punto, suele ser decimal en Python pero Miles en Alemán.
            # En Kleinanzeigen suele ser miles (ej. 1.200). 
            # Si el punto está seguido de 3 números, es miles.
            if re.search(r"\.\d{3}", clean):
                clean = clean.replace(".", "")
            else:
                pass # Es decimal
                
        # Extraer solo el número (ignorar VB u otros textos)
        match = re.search(r"(\d+\.?\d*)", clean)
        if not match:
            return None
        price = float(match.group(1))
        # Ignora precios fakes, simbólicos o marcadores
        if price <= 10 or price in [123, 1234, 1111, 9999]: 
            return None
        return price
    except Exception:
        return None

def analyze_listing(title, description, price, url, image_url="", source="Kleinanzeigen"):
    title_lower = title.lower()
    desc_lower = description.lower()
    
    # 1. Filtro de descarte (Anuncios de "Busco", accesorios, re-ediciones modernas, manuales, etc.)
    # Exigir límites de palabra usando RegEx para evitar que "ministry" filtre "mini" por error
    for ignore in CONDITION_IGNORE:
        if re.search(rf"\b{ignore}\b", title_lower):
            return None
            
    # Filtro de precio mínimo para evitar piezas sueltas
    if price is None or (price < 50 and "reface" not in title_lower and "sr-16" not in title_lower):
        return None
            
    # Identificar el modelo exacto de TODA la base de datos
    # (El filtrado por marca se hace ahora SOLO en la interfaz visual)
    all_models = list(MARKET_VALUES.keys())
    
    # Normalizar string (solo pasarlo a minúsculas, dejamos los espacios para la regex)
    clean_title = title_lower
    
    detected_model = None
    # Ordenar modelos por longitud (de mayor a menor) para que "Minilogue XD" coincida antes que "Minilogue"
    all_models.sort(key=len, reverse=True)
    
    for model in all_models:
        # Separa el modelo por espacios y guiones
        parts = re.split(r"[\s\-]+", model.lower())
        # Escapa cada parte y únelas permitiendo espacios, guiones o NADA entre ellas
        pattern_str = r"[\s\-]*".join([re.escape(p) for p in parts])
        pattern = rf"\b{pattern_str}\b"
        
        if re.search(pattern, clean_title):
            detected_model = model
            break
            
    if not detected_model:
        return None

    # 3. Determinar estado base (Defecto/Piezas vs Funcional)
    is_defekt = any(kw in title_lower or kw in desc_lower for kw in CONDITION_DEFEKT)
    is_mint = any(kw in title_lower or kw in desc_lower for kw in CONDITION_MINT)
    is_poor = any(kw in title_lower or kw in desc_lower for kw in CONDITION_POOR)
    
    # Identificar precio de mercado (Rango low, high)
    market_low, market_high = get_market_price(detected_model)
    if market_low == 0:
        return None
        
    # Calcular promedio para el porcentaje de ahorro base
    market_avg = (market_low + market_high) / 2
    
    # Ajuste fino según condición detectada
    # Si es Defekt, el ahorro se calcula sobre el precio bajo de mercado
    # Si es Mint, sobre el precio alto
    reference_price = market_avg
    if is_defekt:
        reference_price = market_low
    elif is_mint:
        reference_price = market_high
        
    discount = (reference_price - price) / reference_price
    
    opportunity = None
    # Lógica de negocio (40% de ahorro mínimo en defectuosos, 20% en funcionales)
    if is_defekt and discount >= 0.40:
        opportunity = "Gran Margen Defecto"
    elif not is_defekt and discount >= 0.20:
        opportunity = "Buen Precio Funcional"
        
    if opportunity:
        condition_label = "Funcional (Average)"
        if is_defekt:
            condition_label = "Defekt/Bastler"
        elif is_mint:
            condition_label = "Funcional (Mint)"
        elif is_poor:
            condition_label = "Funcional (Gebrauchsspuren)"

        # Generar Borrador de Mensaje en Alemán
        if is_defekt:
            msg = f"Hallo, ich interessiere mich für den {detected_model}. Da das Gerät als defekt/Bastlerware angeboten wird und eine Reparatur Zeit sowie Ersatzteile erfordert, würde ich {int(price * 0.85)}€ inkl. Versand anbieten. Wäre das für Sie in Ordnung? MfG."
        else:
            msg = f"Guten Tag, ist der {detected_model} noch verfügbar? Ich hätte großes Interesse. Befindet er sich in einem voll funktionsfähigen Zustand und wäre ein sicherer Versand möglich? Vielen Dank und beste Grüße."
            
        return {
            "Modelo": detected_model,
            "Estado": condition_label,
            "Precio URL": price,
            "Precio Mercado": f"{int(market_low)} - {int(market_high)} €",
            "Ahorro %": f"{int(discount*100)}%",
            "Plataforma": source,
            "Enlace": url,
            "Imagen": image_url,
            "Reverb": f"https://reverb.com/marketplace?query={detected_model.replace(' ', '+')}&condition=used",
            "Mensaje Borrador": msg,
            "last_seen": datetime.now().timestamp()
        }
    return None

def scrape_all_platforms():
    logging.info("Iniciando escaneo en kleinanzeigen.de y ebay.de con Playwright...")

    results = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="de-DE",
        )
        # Patch navigator.webdriver API
        
        page = context.new_page()

        try:
            seen_links = set()

            # Búsquedas amplias EXCLUSIVAMENTE por marca + categoría
            queries = []
            major_brands = ["Roland", "Korg", "Yamaha", "Akai", "Elektron"]
            
            for brand in TARGET_BRANDS:
                # Variaciones de Synthesizer
                queries.append((f"{brand}-synthesizer", 3 if brand in major_brands else 1))
                queries.append((f"{brand}-synth", 2 if brand in major_brands else 1))
                queries.append((f"{brand}-synthetizer", 1))
                
                # Drum machines y Grooveboxes
                queries.append((f"{brand}-drum-machine", 2 if brand in major_brands else 1))
                queries.append((f"{brand}-groovebox", 1))
                
            total_items = sum(q[1] for q in queries)
            processed_items = 0

            for base_query, pages in queries:
                for page_num in range(1, pages + 1):
                    processed_items += 1
                    search_display = base_query.replace('-', ' ').title()
                    
                    # URL construct with pagination
                    if page_num == 1:
                        url = f"https://www.kleinanzeigen.de/s-musikinstrumente/{base_query}/k0c74"
                    else:
                        url = f"https://www.kleinanzeigen.de/s-musikinstrumente/seite:{page_num}/{base_query}/k0c74"
                    
                    for attempt in range(3):
                        try:
                            page.goto(url, wait_until="domcontentloaded", timeout=15000)
                            page.wait_for_timeout(2000)
                            break # Success
                        except Exception as e:
                            logging.warning(f"Timeout/error cargando {url} (Intento {attempt+1}/3): {e}")
                            if attempt == 2:
                                continue
                            time.sleep(2 ** attempt) # Exponential backoff

                    soup = BeautifulSoup(page.content(), 'html.parser')
                    ads = soup.find_all('article', class_='aditem')
                    logging.info(f"[{search_display} p{page_num}] Encontrados {len(ads)} anuncios.")

                    for ad in ads:
                        title_elem = ad.find('a', class_='ellipsis')
                        desc_elem = ad.find('p', class_='aditem-main--middle--description')
                        price_elem = ad.find('p', class_='aditem-main--middle--price-shipping--price')

                        if not title_elem or not price_elem:
                            continue

                        title = title_elem.text.strip()
                        link = "https://www.kleinanzeigen.de" + title_elem['href']
                        desc = desc_elem.text.strip() if desc_elem else ""
                        price_str = price_elem.text.strip()

                        # Extract thumbnail image if available
                        img_elem = ad.find('img', class_='imagebox-thumbnail')
                        if not img_elem:
                            img_elem = ad.find('img')  # fallback to any img
                        image_url = img_elem.get('src', '') if img_elem else ''

                        price = extract_price(price_str)
                        analysis = analyze_listing(title, desc, price, link, image_url, source="Kleinanzeigen")

                        if analysis and link not in seen_links:
                            seen_links.add(link)
                            results.append(analysis)

            # ----------------------------------------------------
            # EBAY SCRAPING LOOP
            # ----------------------------------------------------
            logging.info("Iniciando escaneo en ebay.de...")
            for brand in TARGET_BRANDS:
                url = f"https://www.ebay.de/sch/i.html?_nkw={brand}+synthesizer&LH_BIN=1&LH_ItemCondition=3000&_ipg=60"
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    page.wait_for_timeout(2000)
                    soup = BeautifulSoup(page.content(), 'html.parser')
                    for link in soup.find_all('a', href=lambda h: h and '/itm/' in h):
                        href = link.get('href').split('?')[0]
                        if href in seen_links: continue
                        seen_links.add(href)
                        parent = link.find_parent('li')
                        if parent:
                            title_el = parent.find(class_=lambda c: c and 'title' in c)
                            price_el = parent.find(class_=lambda c: c and 'price' in c)
                            if title_el and price_el:
                                price = extract_price(price_el.text.strip())
                                img_url = parent.find('img').get('src', '') if parent.find('img') else ''
                                opp = analyze_listing(title_el.text.strip(), "", price, href, img_url, source="eBay")
                                if opp: results.append(opp)
                except Exception as e:
                    logging.error(f"Error parseando tarjeta de eBay: {e}")

            return results
        except Exception as e:
            logging.error(f"Error durante el scraping: {e}")
        finally:
            browser.close()

def main():
    print("🤖 Iniciando Bot Experto en Arbitraje de Sintetizadores (Cloud Version)...")
    
    opportunities = scrape_all_platforms()
    
    if opportunities:
        for opp in opportunities:
            opp["Fecha Agregado"] = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        db = SupabaseDB()
        print(f"Upserting {len(opportunities)} opportunities to Supabase...")
        db.upsert_listings(opportunities)
        print(f"\n✅ Ciclo completado. {len(opportunities)} nuevas/actualizadas.")
    else:
        print("Ciclo vacío o abortado.")

if __name__ == "__main__":
    main()
