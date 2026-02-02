import requests
import certifi
from django.conf import settings

BASE = "https://api.tcgapis.com/api/v1"

def _headers():
    return {"x-api-key": settings.TCGAPIS_API_KEY}

def get_games():
    r = requests.get(f"{BASE}/games", headers=_headers(), timeout=20, verify=certifi.where())
    r.raise_for_status()
    return r.json()

def get_expansions(category_id: int):
    r = requests.get(f"{BASE}/expansions/{category_id}", headers=_headers(), timeout=30, verify=certifi.where())
    r.raise_for_status()
    return r.json()

def get_cards_by_group(group_id: int):
    r = requests.get(f"{BASE}/cards/{group_id}", headers=_headers(), timeout=30, verify=certifi.where())
    r.raise_for_status()
    return r.json()

def get_prices_by_product(product_id: int):
    r = requests.get(f"{BASE}/prices/{product_id}", headers=_headers(), timeout=30, verify=certifi.where())
    r.raise_for_status()
    return r.json()
