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

    res = requests.post(url, headers=headers, data=data)

    print("TOKEN STATUS:", res.status_code)
    print("TOKEN RESPONSE:", res.text)   # 🔥 THIS is key

    try:
        return res.json()["access_token"]
    except Exception:
        raise Exception("Token request failed (see response above)")

# ---------------------------
# SHEET LOGGING
# ---------------------------
def log_to_sheet(sheet, item, niche, price, sold, profit, profit_pct, decision, url):
    sheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        item,
        niche,
        price,
        sold,
        profit,
        profit_pct,
        decision,
        url
    ])


def connect_sheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds_json = os.getenv("GOOGLE_CREDS_JSON")
    creds_dict = json.loads(creds_json)

    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    # ✅ FIXED: must be a string
    sheet = client.open("resale deal finder").sheet1
    return sheet


# ---------------------------
# SEARCH ITEMS
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
        "denim tears hoodie"
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

print("SEARCH STATUS:", res.status_code)
print("SEARCH RAW:", res.text[:200])  # debug first 200 chars

try:
    data = res.json()
except Exception:
    print("JSON FAILED FOR QUERY:", q)
    continue

        all_items.extend(data.get("itemSummaries", []))

    return {"itemSummaries": all_items}


# ---------------------------
# NICHE DETECTION
# ---------------------------
def detect_niche(title):
    title = title.lower()

    if any(x in title for x in ["hoodie", "fleece", "crewneck"]):
        return "hoodie"
    if any(x in title for x in ["jacket", "coat", "nuptse", "arcteryx"]):
        return "jacket"
    if any(x in title for x in ["sneaker", "nike", "adidas", "new balance", "asics", "samba"]):
        return "sneaker"
    if any(x in title for x in ["tee", "shirt", "stussy"]):
        return "shirt"
    if any(x in title for x in ["sunglasses", "oakley"]):
        return "accessory"

    return "general"


# ---------------------------
# SOLD COMPS
# ---------------------------
def get_sold_price_estimate(token, niche, keyword):
    import statistics

    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"

    headers = {
        "Authorization": f"Bearer {token}"
    }

    params = {
        "q": keyword,
        "limit": 20,
        "filter": "buyingOptions:{FIXED_PRICE}"
    }

    res = requests.get(url, headers=headers, params=params)

    try:
        data = res.json()
    except:
        return None

    prices = []

    for item in data.get("itemSummaries", []):
        price = item.get("price", {}).get("value")

        try:
            price = float(price)
            if price > 0:
                prices.append(price)
        except:
            pass

    if len(prices) < 3:
        return None

    prices.sort()
    trimmed = prices[1:-1]

    if not trimmed:
        return statistics.median(prices)

    return statistics.median(trimmed)


# ---------------------------
# DEAL ENGINE
# ---------------------------
def evaluate_deal(price, sold_price):
    try:
        price = float(price)
    except:
        return None

    if not sold_price:
        return None

    resale_estimate = sold_price

    fees = resale_estimate * 0.13
    shipping = 10

    net_profit = resale_estimate - price - fees - shipping
    profit_percent = (net_profit / price) * 100 if price > 0 else 0

    if net_profit >= 20 and profit_percent >= 20:
        label = "BUY"
    elif net_profit >= 8:
        label = "RISK"
    else:
        label = "PASS"

    return net_profit, profit_percent, label


# ---------------------------
# MAIN LOOP
# ---------------------------
def run():
    try:
        print("\n--- SCANNING ---")

        token = get_token()
        sheet = connect_sheet()

        data = get_items(token)
        items = data.get("itemSummaries", [])

        seen = set()

        for item in items:
            title = item.get("title")
            price = item.get("price", {}).get("value")
            url = item.get("itemWebUrl")

            if not title or not price:
                continue

            if title in seen:
                continue
            seen.add(title)

            niche = detect_niche(title)
            sold_price = get_sold_price_estimate(token, niche, title)

            result = evaluate_deal(price, sold_price)
            if not result:
                continue

            net_profit, profit_pct, decision = result

            # ✅ BUY ONLY FILTER
            if BUY_ONLY and decision != "BUY":
                continue

            log_to_sheet(
                sheet,
                title,
                niche,
                price,
                sold_price,
                net_profit,
                profit_pct,
                decision,
                url
            )

            print(title, decision, net_profit)

    except Exception as e:
        print("ERROR:", e)


# ---------------------------
# LOOP
# ---------------------------
while True:
    run()
    time.sleep(300)
