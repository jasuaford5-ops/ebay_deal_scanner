import requests
import base64
import os
import time
import json
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

BUY_ONLY = True


# ---------------------------
# SAFE JSON WRAPPER
# ---------------------------
def safe_request_json(res, label):
    print(f"\n[{label}] STATUS:", res.status_code)
    print(f"[{label}] TEXT:", res.text[:200])

    try:
        return res.json()
    except Exception:
        print(f"❌ NON-JSON RESPONSE: {label}")
        return None


# ---------------------------
# EBAY AUTH
# ---------------------------
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

    res = requests.post(url, headers=headers, data=data, timeout=20)

    print("TOKEN STATUS:", res.status_code)

    data = safe_request_json(res, "TOKEN")

    if not data:
        raise Exception("Token failed")

    return data.get("access_token")


# ---------------------------
# SHEETS
# ---------------------------
def connect_sheet():
    creds_json = os.getenv("GOOGLE_CREDS_JSON")

    creds_dict = json.loads(creds_json)

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    return client.open("resale deal finder").sheet1


# ---------------------------
# EBAY SEARCH
# ---------------------------
def get_items(token):
    queries = [
        "nike tech fleece hoodie",
        "carhartt jacket",
        "stussy tee",
        "arcteryx atom lt",
        "north face nuptse",
        "adidas samba",
        "new balance 1906r",
        "asics gel 1130",
        "sp5der hoodie",
        "denim tears hoodie"
    ]

    all_items = []

    for q in queries:
        url = "https://api.ebay.com/buy/browse/v1/item_summary/search"

        headers = {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"
        }

        params = {
            "q": q,
            "limit": 5,
            "sort": "newlyListed"
        }

        res = requests.get(url, headers=headers, params=params, timeout=20)

        data = safe_request_json(res, f"SEARCH {q}")

        if not data:
            continue

        all_items.extend(data.get("itemSummaries", []))

    return all_items


# ---------------------------
# COMP ESTIMATE
# ---------------------------
def estimate_price(token, keyword):
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"

    headers = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"
    }

    params = {
        "q": keyword,
        "limit": 20
    }

    res = requests.get(url, headers=headers, params=params, timeout=20)

    data = safe_request_json(res, "COMPS")

    if not data:
        return None

    prices = []

    for item in data.get("itemSummaries", []):
        try:
            price = float(item.get("price", {}).get("value", 0))
            if price > 0:
                prices.append(price)
        except:
            pass

    if len(prices) < 3:
        return None

    prices.sort()
    trimmed = prices[1:-1]

    return sum(trimmed) / len(trimmed) if trimmed else sum(prices) / len(prices)


# ---------------------------
# DEAL ENGINE
# ---------------------------
def evaluate(price, comp):
    if not comp:
        return None

    price = float(price)

    fees = comp * 0.13
    shipping = 10

    profit = comp - price - fees - shipping
    profit_pct = (profit / price) * 100 if price > 0 else 0

    if profit >= 20 and profit_pct >= 20:
        return profit, profit_pct, "BUY"
    elif profit >= 8:
        return profit, profit_pct, "RISK"
    else:
        return profit, profit_pct, "PASS"


# ---------------------------
# MAIN LOOP
# ---------------------------
def run():
    print("\n========================")
    print("NEW SCAN RUN")
    print("========================")

    try:
        token = get_token()
        sheet = connect_sheet()

        items = get_items(token)
        print("ITEMS FOUND:", len(items))

        for item in items:
            title = item.get("title")
            price = item.get("price", {}).get("value")
            url = item.get("itemWebUrl")

            if not title or not price:
                continue

            comp = estimate_price(token, title)
            result = evaluate(price, comp)

            if not result:
                continue

            profit, pct, decision = result

            if BUY_ONLY and decision != "BUY":
                continue

            print(title, decision, profit)

            sheet.append_row([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                title,
                price,
                comp,
                profit,
                pct,
                decision,
                url
            ])

    except Exception as e:
        print("🔥 CRASH:", type(e).__name__, str(e))


# ---------------------------
# LOOP
# ---------------------------
while True:
    run()
    time.sleep(300)
