import requests
import base64
import os
import time
import json
from datetime import datetime


# ---------------------------
# EBAY AUTH
# ---------------------------
def get_token():
    client_id = os.getenv("EBAY_CLIENT_ID")
    client_secret = os.getenv("EBAY_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise Exception("Missing eBay credentials")

    creds = f"{client_id}:{client_secret}"
    encoded = base64.b64encode(creds.encode()).decode()

    url = "https://api.ebay.com/identity/v1/oauth2/token"

    headers = {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope"
    }

    res = requests.post(url, headers=headers, data=data)

    print("TOKEN STATUS:", res.status_code)

    try:
        token_data = res.json()
    except Exception:
        print("TOKEN RAW RESPONSE:", res.text)
        raise

    return token_data["access_token"]


# ---------------------------
# SEARCH QUERIES
# ---------------------------
def get_items(token):
    queries = [
        "nike tech fleece hoodie",
        "carhartt jacket active",
        "stussy tee vintage",
        "arcteryx atom lt jacket",
        "north face nuptse 700",
        "adidas samba og",
        "new balance 1906r",
        "asics gel 1130",
        "sp5der hoodie",
        "denim tears hoodie",
        "oakley sutro sunglasses",
        "gymshark compression shirt",
        "birkenstock stussy sandals"
    ]

    all_items = []

    for q in queries:
        url = "https://api.ebay.com/buy/browse/v1/item_summary/search"

        headers = {
            "Authorization": f"Bearer {token}"
        }

        params = {
            "q": q,
            "limit": 5,
            "sort": "newlyListed"
        }

        res = requests.get(url, headers=headers, params=params)

        print(f"\nQUERY: {q}")
        print("STATUS:", res.status_code)

        # SAFE JSON HANDLING (prevents your crash)
        try:
            data = res.json()
        except Exception:
            print("RAW RESPONSE:", res.text[:300])
            continue

        items = data.get("itemSummaries", [])
        all_items.extend(items)

    return {"itemSummaries": all_items}


# ---------------------------
# MAIN LOOP
# ---------------------------
def run():
    try:
        print("\n--- RUNNING SCAN ---")

        token = get_token()
        data = get_items(token)

        items = data.get("itemSummaries", [])

        print("\nTOTAL ITEMS:", len(items))

        for item in items:
            title = item.get("title")
            price = item.get("price", {}).get("value")
            url = item.get("itemWebUrl")

            print(title, "-", price)

    except Exception as e:
        print("ERROR:", e)


# ---------------------------
# LOOP
# ---------------------------
while True:
    run()
    time.sleep(300)
