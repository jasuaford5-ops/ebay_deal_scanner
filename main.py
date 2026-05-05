import requests
import base64
import os
import time

def get_token():
    client_id = os.getenv("EBAY_CLIENT_ID")
    client_secret = os.getenv("EBAY_CLIENT_SECRET")

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
    res.raise_for_status()
    return res.json()["access_token"]

def get_items(token):
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"

    headers = {
        "Authorization": f"Bearer {token}"
    }

    params = {
        "q": "nike hoodie",
        "limit": 5,
        "sort": "newlyListed"
    }

    res = requests.get(url, headers=headers, params=params)
    res.raise_for_status()
    return res.json()

def run():
    try:
        token = get_token()
        data = get_items(token)

        print("\n--- LIVE LISTINGS ---")
        for item in data.get("itemSummaries", []):
            title = item.get("title")
            price = item.get("price", {}).get("value")
            print(title, price)

    except Exception as e:
        print("ERROR:", e)

while True:
    run()
    time.sleep(300)
