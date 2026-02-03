import os
import time
import requests
import certifi
from dotenv import load_dotenv

load_dotenv()

BASE = "https://api.tcgapis.com/api/v1"
API_KEY = os.getenv("TCGAPIS_API_KEY")

class RateLimitError(Exception):
    pass

def _headers():
    if not API_KEY:
        raise RuntimeError("Missing TCGAPIS_API_KEY in .env")
    return {"x-api-key": API_KEY}

def fetch_price_by_product_id(product_id: int, *, max_wait_seconds: int = 60) -> float | None:
    """
    Fetch a single market price from TCGAPIs using the fast endpoint:
      GET /api/v1/prices/{productId}

    Returns a float (best guess market price), or None if no price found.
    Raises RateLimitError if rate limit persists beyond max_wait_seconds.
    """
    url = f"{BASE}/prices/{int(product_id)}"

    backoff = 2.0
    waited = 0.0

    while True:
        resp = requests.get(
            url,
            headers=_headers(),
            timeout=20,
            verify=certifi.where(),
        )

        # rate limited
        if resp.status_code == 429:
            if waited >= max_wait_seconds:
                raise RateLimitError(f"429 persisted > {max_wait_seconds}s for productId={product_id}")
            time.sleep(backoff)
            waited += backoff
            backoff = min(backoff * 2, 15.0)
            continue

        resp.raise_for_status()
        data = resp.json()

        # TCGAPIs responses vary; handle a few common shapes safely
        # Example possibilities:
        # {success:true, data:{prices:[{marketPrice:...}]}}
        # {success:true, data:{price:{market:...}}}
        d = data.get("data") or {}

        # try list form
        prices = d.get("prices")
        if isinstance(prices, list) and prices:
            p0 = prices[0] or {}
            for key in ("marketPrice", "market", "price", "midPrice"):
                val = p0.get(key)
                if isinstance(val, (int, float)):
                    return float(val)

        # try dict form
        price_obj = d.get("price") or d.get("pricing") or {}
        if isinstance(price_obj, dict):
            for key in ("market", "marketPrice", "price", "mid"):
                val = price_obj.get(key)
                if isinstance(val, (int, float)):
                    return float(val)

        return None
