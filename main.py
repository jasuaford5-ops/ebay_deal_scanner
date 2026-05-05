import requests
import base64
import os
import time
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
    res.raise_for_status()

    return res.json()["access_token"]


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

        try:
            data = res.json()
        except:
            print("Bad response for:", q)
            continue

        all_items.extend(data.get("itemSummaries", []))

    return {"itemSummaries": all_items}

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

def get_sold_price_estimate(token, niche, keyword):
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"

    headers = {
        "Authorization": f"Bearer {token}"
    }

    params = {
        "q": f"{keyword}",
        "filter": "buyingOptions:{AUCTION|FIXED_PRICE},sold:true",
        "limit": 10
    }

    res = requests.get(url, headers=headers, params=params)

    try:
        data = res.json()
    except:
        return None

    prices = []

    for item in data.get("itemSummaries", []):
        price = item.get("price", {}).get("value")
        if price:
            try:
                prices.append(float(price))
            except:
                pass

    if not prices:
        return None

    return sum(prices) / len(prices)
# ---------------------------
# DEAL ENGINE (PHASE 1)
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

    if net_profit >= 30 and profit_percent > 25:
        label = "BUY"
    elif net_profit >= 10:
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
        data = get_items(token)

        items = data.get("itemSummaries", [])

        seen = set()

        for item in items:
            title = item.get("title")
            price = item.get("price", {}).get("value")
            url = item.get("itemWebUrl")

            if not title or not price:
                continue

            # prevent duplicate spam
            if title in seen:
                continue
            seen.add(title)

            niche = detect_niche(title)
            sold_price = get_sold_price_estimate(token, niche, title)

            result = evaluate_deal(price, sold_price)

            if not result:
                continue

            net_profit, profit_percent, label = result

            print("\n--------------------")
            print("ITEM:", title)
            print("NICHE:", niche)
            print("BUY PRICE:", price)
            print("SOLD AVG:", round(sold_price, 2) if sold_price else None)
            print("NET PROFIT:", round(net_profit, 2))
            print("PROFIT %:", round(profit_percent, 2))
            print("DECISION:", label)
            print("LINK:", url)

    except Exception as e:
        print("ERROR:", e)


# ---------------------------
# LOOP (Railway runtime)
# ---------------------------
while True:
    run()
    time.sleep(300)
