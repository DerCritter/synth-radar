import requests
import json
import re

URL = "https://wnoiyxgdbemamajebqom.supabase.co/rest/v1/listings"
HEADERS = {
    "apikey": "sb_publishable_VCnH38uDOJvfet7bJHRnAw_9VZaDSmp",
    "Authorization": "Bearer sb_publishable_VCnH38uDOJvfet7bJHRnAw_9VZaDSmp",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

JUNK_KEYWORDS = [
    "case", "flightcase", "cover", "dust", "decksaver", "manual", "anleitung", 
    "knob", "fader", "pot", "psu", "power supply", "netzteil", "cable", "kabel", 
    "stand", "ständer", "gigbag", "bag", "tasche", "box", "ovp", "box only", 
    "decal", "sticker", "trafo", "transformer", "transformador", "seitenteile", 
    "holzseitenteile", "wood panels", "wooden sides", "rack ears", "rackmount", 
    "holz", "wood", "stromkabel"
]

ACCESSORY_KEYWORDS = [
    "cartridge", "memory", "ram", "rom", "card", "pedal", "expansion", 
    "voice", "voice card"
]

DEFECTIVE_KEYWORDS = [
    "defekt", "bastler", "parts", "repair", "reparieren"
]

# Fetch all
r = requests.get(URL + "?select=url,modelo", headers=HEADERS)
if not r.ok:
    print("Fetch error:", r.text)
    exit(1)

listings = r.json()
print(f"Total listings: {len(listings)}")

deleted = 0
updated = 0

for item in listings:
    url_val = item.get("url", "")
    title = item.get("modelo", "").lower()
    if not url_val:
        continue
    
    # URL might contain title slugs in Kleinanzeigen
    search_string = (title + " " + url_val).lower()
    
    is_junk = any(re.search(rf"\b{re.escape(k)}\b", search_string) for k in JUNK_KEYWORDS)
    if is_junk:
        del_r = requests.delete(URL + f"?url=eq.{url_val}", headers=HEADERS)
        deleted += 1
        continue
        
    is_acc = any(k in title for k in ACCESSORY_KEYWORDS)
    if is_acc:
        # Patch the row
        payload = {
            "ahorro_porcentaje": "0%",
            "estado": "Accesorio / Funcional" # Base fallback, will be overwritten if defective
        }
        is_def = any(k in title for k in DEFECTIVE_KEYWORDS)
        if is_def:
            payload["estado"] = "Accesorio / Defekt/Bastler"
            
        patch_r = requests.patch(URL + f"?url=eq.{url_val}", headers=HEADERS, json=payload)
        updated += 1
        continue

print(f"Cleanup done! Deleted {deleted} junk items. Updated {updated} accessory items.")
