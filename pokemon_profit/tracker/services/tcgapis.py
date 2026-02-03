import time
import requests
import certifi
from django.conf import settings

BASE = "https://api.tcgapis.com/api/v1"

def _headers():
    return {"x-api-key": settings.TCGAPIS_API_KEY}

def _get_json_with_backoff(url: str, params: dict | None = None, timeout: int = 30, max_wait_seconds: int = 15 * 60):
    """
    Keeps retrying on 429 until success or max_wait_seconds is exceeded.
    Uses exponential backoff, capped at 5 minutes.
    """
    start = time.time()
    backoff = 5  # start at 5s, then 10, 20, 40...

    while True:
        r = requests.get(url, headers=_headers(), params=params, timeout=timeout, verify=certifi.where())

        if r.status_code != 429:
            r.raise_for_status()
            return r.json()

        # 429: Too Many Requests
        elapsed = time.time() - start
        if elapsed >= max_wait_seconds:
            raise RuntimeError(
                f"TCGAPIs rate limit persisted for {int(elapsed)}s. "
                f"Try again later or increase max_wait_seconds."
            )

        # if they ever add Retry-After later, honor it
        ra = r.headers.get("Retry-After")
        if ra and ra.replace(".", "", 1).isdigit():
            wait_s = float(ra)
        else:
            wait_s = backoff

        print(f"[TCGAPIs] 429 rate limited. Waiting {wait_s:.1f}s then retrying...")
        time.sleep(wait_s)
        backoff = min(backoff * 2, 300)  # cap at 5 minutes
        
def get_expansions(category_id: int, page: int = 1):
    url = f"{BASE}/expansions/{category_id}"
    return _get_json_with_backoff(url, params={"page": page}, timeout=30)

def get_cards_by_group(group_id: int, page: int = 1, search: str | None = None):
    url = f"{BASE}/cards/{group_id}"
    params = {"page": page}
    if search:
        params["search"] = search
    return _get_json_with_backoff(url, params=params, timeout=30)

def get_prices_by_product(product_id: int):
    url = f"{BASE}/prices/{product_id}"
    return _get_json_with_backoff(url, params=None, timeout=30)