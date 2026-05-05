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
    print("TOKEN RAW:", res.text)

    # 🧠 SAFETY CHECK (IMPORTANT)
    if res.status_code != 200:
        raise Exception("Token failed")

    try:
        return res.json().get("access_token")
    except Exception:
        print("❌ BAD JSON RESPONSE:", res.text)
        raise

def safe_json(res, label=""):
    print(f"\n[{label}] STATUS:", res.status_code)
    print(f"[{label}] RAW:", res.text[:300])

    try:
        return res.json()
    except Exception:
        print(f"❌ JSON FAILED FOR {label}")
        return None
# ---------------------------
# GOOGLE SHEETS
# ---------------------------
def connect_sheet():
    creds_json = os.getenv("GOOGLE_CREDS_JSON")
    if not creds_json:
        raise Exception("Missing GOOGLE_CREDS_JSON")

    creds_dict = json.loads(creds_json)

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    return client.open("resale deal finder").sheet1


def log_to_sheet(sheet, row):
    sheet.append_row(row)


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

       res = requests.get(url, headers=headers, params=params)
data = safe_json(res, f"SEARCH:{q}")

if not data:
    continue
        # 🔥 CRITICAL DEBUG
        print("\n--- REQUEST DEBUG ---")
        print("QUERY:", q)
        print("STATUS:", res.status_code)
        print("HEADERS:", res.headers.get("Content-Type"))
        print("BODY (first 300 chars):", res.text[:300])

        # ❌ NEVER crash here again
        if "json" not in str(res.headers.get("Content-Type", "")):
            print("❌ NON-JSON RESPONSE, skipping")
            continue

        try:
            data = res.json()
        except Exception as e:
            print("JSON PARSE FAILED:", e)
            continue

        all_items.extend(data.get("itemSummaries", []))

    return all_items


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
# COMP ESTIMATE (simple median fallback)
# ---------------------------
def estimate_price(token, keyword):
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"

    headers = {
        "Authorization": f"Bearer {token}"
    }

    params = {
        "q": keyword,
        "limit": 20
    }

    res = requests.get(url, headers=headers, params=params)

    try:
        data = safe_json(res, "SOLD_COMPS")

if not data:
    return None
    except:
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
    try:
        print("\n--- SCANNING ---")

        token = get_token()
        print("TOKEN OK")

        sheet = connect_sheet()
        print("SHEET CONNECTED")

        items = get_items(token)
        print("ITEMS FETCHED:", len(items))

    except Exception as e:
        print("\n🔥 FULL CRASH ERROR:")
        print(type(e).__name__)
        print(str(e))


# ---------------------------
# LOOP
# ---------------------------
while True:
    run()
    time.sleep(300)
