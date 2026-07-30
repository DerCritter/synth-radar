import os
import re
from supabase_client import SupabaseDB

JUNK_KEYWORDS = [
    "case", "flightcase", "cover", "dust", "decksaver", "manual", "anleitung", 
    "knob", "fader", "pot", "psu", "power supply", "netzteil", "cable", "kabel", 
    "stand", "ständer", "gigbag", "bag", "tasche", "box", "ovp", "box only", 
    "decal", "sticker"
]

def main():
    db = SupabaseDB()
    if not db.client:
        print("Supabase client not initialized. Check your environment variables.")
        return

    listings = db.get_listings()
    print(f"Total listings fetched: {len(listings)}")
    
    to_delete_urls = []
    
    for item in listings:
        url = item.get("Enlace", "")
        if not url:
            continue
            
        url_lower = url.lower()
        url_parts = re.split(r'[-/.]', url_lower)
        
        is_junk = False
        for junk in JUNK_KEYWORDS:
            # Check exact part match for single words
            if junk in url_parts:
                is_junk = True
                break
            # Check for multi-word keywords separated by dash
            if junk.replace(' ', '-') in url_lower:
                is_junk = True
                break
                
        if is_junk:
            to_delete_urls.append(url)
            
    print(f"Found {len(to_delete_urls)} junk listings to delete.")
    
    for url in to_delete_urls:
        try:
            db.client.table("listings").delete().eq("url", url).execute()
            print(f"Deleted: {url}")
        except Exception as e:
            print(f"Error deleting {url}: {e}")
            
    print("Cleanup complete.")

if __name__ == "__main__":
    main()
