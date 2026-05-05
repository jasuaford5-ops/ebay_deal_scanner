import requests
import base64
import os
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime


# ---------------------------
# EBAY AUTH
# ---------------------------
def get_token():
    client_id = os.getenv("EBAY_CLIENT_ID")
    client_secret = os.getenv("EBAY_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise Exception("Missing eBay API keys")

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


# ---------------------------
# EBAY SEARCH
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
        "oakley sunglasses sutro",
        "gymshark compression shirt",
        "birkensock stussy sandals"
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
        res.raise_for_status()

        data = res.json()
        all_items.extend(data.get("itemSummaries", []))

    return {"itemSummaries": all_items}


# ---------------------------
# GOOGLE SHEETS CONNECT
# ---------------------------
def connect_sheet():
    creds_dict = json.loads(os.getenv("GOOGLE_CREDS_JSON"))

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    sheet_name = os.getenv("SHEET_NAME")

    return client.open(sheet_name).sheet1


# ---------------------------
# MAIN LOOP
# ---------------------------
def run():
    try:
        print("\n--- RUNNING SCAN ---")

        token = get_token()
        data = get_items(token)
        sheet = connect_sheet()

        items = data.get("itemSummaries", [])

        for item in items:
            title = item.get("title")
            price = item.get("price", {}).get("value")
            url = item.get("itemWebUrl")
            item_id = item.get("itemId")

            row = [
                title,
                price,
                url,
                item_id,
                datetime.now().isoformat()
            ]

            sheet.append_row(row)
            print("Added:", title)

    except Exception as e:
        print("ERROR:", e)


# ---------------------------
# LOOP
# ---------------------------
while True:
    run()
    time.sleep(300)
