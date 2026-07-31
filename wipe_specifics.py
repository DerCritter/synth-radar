import requests
URL = "https://wnoiyxgdbemamajebqom.supabase.co/rest/v1/listings"
HEADERS = {
    "apikey": "sb_publishable_VCnH38uDOJvfet7bJHRnAw_9VZaDSmp",
    "Authorization": "Bearer sb_publishable_VCnH38uDOJvfet7bJHRnAw_9VZaDSmp",
}

# Delete specific false positives based on their exact price
prices_to_delete = [61.75, 68.03, 79, 89]

for p in prices_to_delete:
    r = requests.delete(URL + f"?precio=eq.{p}", headers=HEADERS)
    print(f"Deleted items with price {p}: {r.status_code}")

